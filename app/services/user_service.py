"""Serviço de gerenciamento de usuários.

Este módulo fornece a camada de serviço para todas as operações relacionadas a usuários,
incluindo registro, autenticação, ativação de conta, reset de senha, e gerenciamento de perfil.

Classes principais:
    - UserService: Serviço principal com métodos para operações de usuário
    - UserOperationStatus: Enum com status de resultados de operações
    - UserActivationResult: Dataclass com resultado de operações de usuário
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from flask import current_app, render_template, url_for
from flask_login import login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.autenticacao import User
from .email_service import EmailValidationService
from .token_service import JWT_action, JWTService


class UserOperationStatus(Enum):
    """Status das operações de usuário."""
    SUCCESS = 0
    USER_NOT_FOUND = 1
    USER_ALREADY_ACTIVE = 2
    USER_INACTIVE = 3
    INVALID_TOKEN = 4
    TOKEN_EXPIRED = 5
    INVALID_UUID = 6
    SEND_EMAIL_ERROR = 7
    DATABASE_ERROR = 8
    INVALID_CREDENTIALS = 9
    UNKNOWN = 99


@dataclass
class UserRegistrationResult:
    """Resultado da operação de registro de usuário."""
    status: UserOperationStatus  # Status da operação (SUCCESS, DATABASE_ERROR, etc.)
    user: Optional[User] = None  # Instância do usuário criado (se sucesso)
    token: Optional[str] = None  # Token JWT para ativação de conta via email
    email_sent: bool = False  # Indica se o email de ativação foi enviado com sucesso
    error_message: Optional[str] = None  # Mensagem de erro detalhada (se falha)


@dataclass
class UserActivationResult:
    """Resultado da operação de ativação de usuário."""
    status: UserOperationStatus  # Status da operação (SUCCESS, INVALID_TOKEN, USER_NOT_FOUND, etc.)
    user: Optional[User] = None  # Instância do usuário ativado (se sucesso)
    error_message: Optional[str] = None  # Mensagem de erro detalhada (se falha)

@dataclass
class PasswordResetResult:
    """Resultado da operação de reset de senha."""
    status: UserOperationStatus = UserOperationStatus.UNKNOWN
    user: Optional[User] = None
    error_message: Optional[str] = None


class UserService:
    """Serviço para operações relacionadas a usuários.

    Utiliza uma sessão SQLAlchemy configurável para permitir uso em diferentes contextos,
    como testes ou transações customizadas.
    """
    # Sessão padrão a ser utilizada quando nenhuma sessão é fornecida
    _default_session = db.session

    @classmethod
    def set_default_session(cls, session):
        """Define a sessão padrão a ser utilizada pelo serviço.

        Args:
            session: Sessão SQLAlchemy a ser utilizada como padrão
        """
        cls._default_session = session

    @classmethod
    def registrar_usuario(cls,
                          nome: str,
                          email: str,
                          password: str,
                          email_service,
                          session=None,
                          auto_commit: bool = True) -> UserRegistrationResult:
        """Registra um novo usuário no sistema.

        Args:
            nome (str): Nome completo do usuário
            email (str): Email do usuário (será normalizado)
            password (str): Senha em texto plano (será hasheada)
            email_service (EmailService): Instância do serviço de email
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            UserRegistrationResult: Resultado da operação com usuário e token
        """
        if session is None:
            session = cls._default_session

        try:
            # Cria o usuário
            usuario = User()
            usuario.nome = nome
            usuario.email = email  # Será normalizado pelo setter
            usuario.ativo = False
            usuario.password = password  # Será hasheado pelo setter

            session.add(usuario)
            session.flush()
            session.refresh(usuario)

            # Gera token e envia email de confirmação
            token, email_sent = UserService._enviar_email_ativacao(usuario, email_service)

            if auto_commit:
                session.commit()
                current_app.logger.info("Usuário registrado: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Usuário marcado para registro (sem commit): %s" % (usuario.email,))

            return UserRegistrationResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario,
                    token=token,
                    email_sent=email_sent
            )

        except ValueError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro ao registrar usuário: %s" % (str(e),))
            return UserRegistrationResult(
                    status=UserOperationStatus.UNKNOWN,
                    error_message=str(e)
            )
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error("Erro de banco de dados ao registrar usuário: %s" % (str(e),))
            return UserRegistrationResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @classmethod
    def ativar_conta(cls,
                     usuario: User,
                     session=None,
                     auto_commit: bool = True) -> bool:
        """Confirma o email do usuário, ativando sua conta.

        Args:
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True)
        """
        if session is None:
            session = cls._default_session

        try:
            if usuario.ativo:
                current_app.logger.warning(
                        "Tentativa de ativar conta já ativa: %s" % (usuario.email,))
                return True  # Já está confirmado, não é erro

            usuario.ativo = True
            usuario.dta_validacao_email = datetime.now()

            if auto_commit:
                session.commit()
                current_app.logger.info("Conta ativada para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Conta marcada para ativação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao ativar conta do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @classmethod
    def desativar_conta(cls,
                        usuario: User,
                        session=None,
                        auto_commit: bool = True) -> bool:
        """Desconfirma o email do usuário, inativando sua conta.

        Args:
            usuario (User): Instância do usuário
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se a operação foi bem-sucedida

        Raises:
            SQLAlchemyError: Em caso de erro na transação (apenas se auto_commit=True)
        """
        if session is None:
            session = cls._default_session

        try:
            if not usuario.ativo:
                current_app.logger.warning(
                        "Tentativa de desativar conta inativa: %s" % (usuario.email,))
                return True  # Não está confirmado, não é erro

            usuario.ativo = False
            usuario.dta_validacao_email = None

            if auto_commit:
                session.commit()
                current_app.logger.info("Conta desativada para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Conta marcada para desativação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao desativar conta do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def pode_logar(usuario: User) -> bool:
        """Verifica se o usuário está ativo e pode efetuar login.

        Args:
            usuario (User): Instância do usuário

        Returns:
            bool: True se o usuário pode logar, False caso contrário
        """
        if not usuario.ativo:
            current_app.logger.warning("Usuário inativo tentou logar: %s" % (usuario.email,))
            return False
        return True

    @staticmethod
    def verificar_idade_senha(usuario: User) -> Optional[int]:
        """Verifica a idade da senha em dias.

        Args:
            usuario (User): Instância do usuário

        Returns:
            Optional[int]: Idade da senha em dias, ou None se não houver data registrada
        """
        if usuario.dta_ultima_alteracao_senha is None:
            return None

        from datetime import datetime
        idade = datetime.now() - usuario.dta_ultima_alteracao_senha
        return idade.days

    @staticmethod
    def ativar_usuario_por_token(token: str) -> UserActivationResult:
        """Valida o email de um usuário através de um token JWT.

        Args:
            token (str): Token JWT de validação de email

        Returns:
            UserActivationResult: Resultado da validação
        """
        claims = JWTService.verify(token)

        if not claims.valid:
            current_app.logger.error("Token inválido: %s" % (claims.reason,))
            return UserActivationResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message=f"Token inválido: {claims.reason}"
            )

        if claims.action != JWT_action.VALIDAR_EMAIL:
            current_app.logger.error("Ação de token inválida: %s" % (claims.action,))
            return UserActivationResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        usuario = User.get_by_email(claims.sub)
        if usuario is None:
            current_app.logger.warning("Tentativa de validação de email para usuário inexistente")
            return UserActivationResult(
                    status=UserOperationStatus.USER_NOT_FOUND,
                    error_message="Usuário não encontrado"
            )

        if usuario.ativo:
            current_app.logger.info("Usuário %s já estava ativo" % (usuario.email,))
            return UserActivationResult(
                    status=UserOperationStatus.USER_ALREADY_ACTIVE,
                    user=usuario,
                    error_message="Usuário já está ativo"
            )

        # Confirma o email
        UserService.ativar_conta(usuario)
        current_app.logger.info("Email validado com sucesso para %s" % (usuario.email,))

        return UserActivationResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario
        )

    @classmethod
    def efetuar_login(cls,
                      usuario: User,
                      remember_me: bool = False,
                      session=None,
                      auto_commit: bool = True) -> bool:
        """Efetua o login do usuário no sistema utilizando Flask-Login.

        Args:
            usuario (User): Instância do usuário
            remember_me (bool): Se True, mantém o usuário logado por mais tempo
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            bool: True se o login foi bem-sucedido

        Raises:
            ValueError: Se o usuário não estiver ativo
            SQLAlchemyError: Em caso de erro na transação
        """
        if session is None:
            session = cls._default_session

        try:
            if not UserService.pode_logar(usuario):
                raise ValueError(f"Usuário {usuario.email} não está ativo")

            # Efetua login usando Flask-Login
            login_user(usuario, remember=remember_me)
            current_app.logger.info("Login efetuado para usuário: %s" % (usuario.email,))

            # Atualiza timestamp de último login
            usuario.ultimo_login = db.func.now()

            if auto_commit:
                session.commit()
                current_app.logger.info(
                    "Informação sobre último login de %s atualizada" % (usuario.email,))
            else:
                current_app.logger.info(
                        "Informação sobre último login de %s marcada para atualizar" % (
                            usuario.email,))

            return True

        except ValueError:
            raise  # Re-propaga erro de validação
        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao efetuar login do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @staticmethod
    def efetuar_logout(usuario: User) -> bool:
        """Efetua o logout do usuário do sistema utilizando Flask-Login.

        Args:
            usuario (User): Instância do usuário

        Returns:
            bool: True se o logout foi bem-sucedido
        """
        try:
            user_email = usuario.email  # Captura antes do logout
            logout_user()

            current_app.logger.info("Logout efetuado para usuário: %s" % (user_email,))
            return True

        except Exception as e:
            current_app.logger.error("Erro ao efetuar logout: %s" % (str(e),))
            return False

    @classmethod
    def atualizar_perfil(cls, usuario: User,
                         novo_nome: str,
                         nova_foto=None,
                         remover_foto: bool = False,
                         session=None,
                         auto_commit: bool = True) -> UserActivationResult:
        """Atualiza o perfil do usuário (nome e foto).

        Args:
            usuario (User): Instância do usuário
            novo_nome (str): Novo nome do usuário
            nova_foto: Arquivo de foto (FileStorage) ou None
            remover_foto (bool): Se True, remove a foto atual
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            UserActivationResult: Resultado da operação
        """
        if session is None:
            session = cls._default_session

        try:
            # Valida que o nome não está vazio
            if not novo_nome or not novo_nome.strip():
                return UserActivationResult(
                        status=UserOperationStatus.UNKNOWN,
                        error_message="Nome não pode ser vazio"
                )

            # Atualiza o nome
            nome_anterior = usuario.nome
            nome_mudou = novo_nome.strip() != nome_anterior
            usuario.nome = novo_nome.strip()

            if nome_mudou:
                current_app.logger.info(
                        "Nome alterado para usuário %s: '%s' -> '%s'" %
                        (usuario.email, nome_anterior, usuario.nome))

            # Processa foto com sistema de priorização:
            # 1. remover_foto: Se True, remove a foto atual
            # 2. nova_foto: Upload de arquivo (pode ser cropada ou original)
            # Este sistema evita conflitos quando múltiplas ações são enviadas
            if remover_foto:
                usuario.foto = None
                current_app.logger.info("Foto removida para usuário %s" % (usuario.email,))
            elif nova_foto and nova_foto.filename:
                from app.services.imageprocessing_service import ImageProcessingError
                try:
                    usuario.foto = nova_foto
                    current_app.logger.info("Foto atualizada para usuário %s" % (usuario.email,))
                except ImageProcessingError as e:
                    if auto_commit:
                        session.rollback()
                    return UserActivationResult(
                            status=UserOperationStatus.UNKNOWN,
                            error_message=f"Erro ao processar imagem: {str(e)}"
                    )
                except ValueError as e:
                    if auto_commit:
                        session.rollback()
                    return UserActivationResult(
                            status=UserOperationStatus.UNKNOWN,
                            error_message=str(e)
                    )

            if auto_commit:
                session.commit()
                current_app.logger.info("Perfil salvo para usuário %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Perfil marcado para atualização (sem commit) para usuário %s" %
                        (usuario.email,))

            return UserActivationResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao atualizar perfil do usuário %s: %s" % (usuario.email, str(e)))
            return UserActivationResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @staticmethod
    def solicitar_reset_senha(email: str, email_service) -> PasswordResetResult:
        """Envia email com token para alteração de senha.

        Args:
            email (str): Email do usuário (será normalizado)
            email_service (EmailService): Instância do serviço de email

        Returns:
            PasswordResetResult: Resultado da operação
        """
        try:
            email_normalizado = EmailValidationService.normalize(email)
        except ValueError:
            current_app.logger.warning("Email inválido fornecido: %s" % (email,))
            # Por segurança, retorna SUCCESS mesmo com email inválido
            return PasswordResetResult(status=UserOperationStatus.SUCCESS)

        usuario = User.get_by_email(email_normalizado)
        if usuario is None:
            current_app.logger.warning(
                    "Pedido de reset de senha para usuário inexistente (%s)" % (email_normalizado,))
            # Por segurança, retorna SUCCESS mesmo se usuário não existir
            return PasswordResetResult(status=UserOperationStatus.SUCCESS)

        # Gera token e envia email
        token = JWTService.create(JWT_action.RESET_PASSWORD, sub=usuario.email)
        body = render_template('auth/email/email_new_password.jinja2',
                               nome=usuario.nome,
                               url=url_for('auth.reset_password', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                          subject="Altere a sua senha",
                                          text_body=body)

        if not result.success:
            current_app.logger.error("Erro ao enviar email de reset para %s" % (usuario.email,))
            return PasswordResetResult(
                    status=UserOperationStatus.SEND_EMAIL_ERROR,
                    user=usuario,
                    error_message="Erro no envio do email"
            )

        current_app.logger.info("Email de reset de senha enviado para %s" % (usuario.email,))
        return PasswordResetResult(
                status=UserOperationStatus.SUCCESS,
                user=usuario
        )

    @classmethod
    def redefinir_senha_por_token(cls,
                                   token: str,
                                   nova_senha: str,
                                   session=None,
                                   auto_commit: bool = True) -> PasswordResetResult:
        """Redefine a senha de um usuário através de um token JWT.

        Args:
            token (str): Token JWT de redefinição de senha
            nova_senha (str): Nova senha em texto plano (será hasheada)
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.
            auto_commit (bool): Se True, faz commit automaticamente. Se False, apenas
                               atualiza o objeto (útil quando chamado dentro de outra transação).

        Returns:
            PasswordResetResult: Resultado da redefinição
        """
        if session is None:
            session = cls._default_session

        # Valida o token
        resultado_token = JWTService.verify(token)

        if not resultado_token.valid:
            current_app.logger.error("Token inválido: %s" % (resultado_token.reason,))
            if resultado_token.reason == "expired":
                return PasswordResetResult(
                        status=UserOperationStatus.TOKEN_EXPIRED,
                        error_message="Token expirado"
                )
            return PasswordResetResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message=f"Token inválido: {resultado_token.reason}"
            )

        if resultado_token.action != JWT_action.RESET_PASSWORD:
            current_app.logger.error("Ação de token inválida: %s" % (resultado_token.action,))
            return PasswordResetResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        if resultado_token.sub is None:
            current_app.logger.error("Token sem subject")
            return PasswordResetResult(
                    status=UserOperationStatus.INVALID_TOKEN,
                    error_message="Token inválido"
            )

        # Busca o usuário
        usuario = User.get_by_email(resultado_token.sub)
        if usuario is None:
            current_app.logger.warning("Tentativa de reset de senha para usuário inexistente")
            return PasswordResetResult(
                    status=UserOperationStatus.USER_NOT_FOUND,
                    error_message="Usuário não encontrado"
            )

        # Redefine a senha
        try:
            usuario.password = nova_senha  # Será hasheada pelo setter

            if auto_commit:
                session.commit()
                current_app.logger.info("Senha redefinida com sucesso para %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Senha marcada para redefinição (sem commit): %s" % (usuario.email,))

            return PasswordResetResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario
            )

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao redefinir senha do usuário %s: %s" % (usuario.email, str(e)))
            return PasswordResetResult(
                    status=UserOperationStatus.DATABASE_ERROR,
                    error_message=str(e)
            )

    @staticmethod
    def _enviar_email_ativacao(usuario: User, email_service) -> tuple[str, bool]:
        """Metodo auxiliar privado para enviar email de ativação/confirmação.

        Args:
            usuario (user): Instância do usuário
            email_service (EmailService): Instância do serviço de email

        Returns:
            tuple[str, bool]: (token gerado, sucesso no envio)
        """
        token = JWTService.create(action=JWT_action.VALIDAR_EMAIL,
                                  sub=usuario.email)
        current_app.logger.debug("Token de ativação por email: %s" % (token,))

        body = render_template('auth/email/account_activation.jinja2',
                               nome=usuario.nome,
                               url=url_for('auth.ativar_usuario', token=token, _external=True))
        result = email_service.send_email(to=usuario.email,
                                          subject="Ative sua conta e confirme o seu email",
                                          text_body=body)

        email_sent = result.success
        if not email_sent:
            current_app.logger.error(
                    "Erro no envio do email de ativação para %s" % (usuario.email,))

        return token, email_sent
