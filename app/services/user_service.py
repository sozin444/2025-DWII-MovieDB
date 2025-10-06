from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from flask import current_app, render_template, url_for
from sqlalchemy.exc import SQLAlchemyError

from app import db
from .token_service import JWT_action, JWTService, TokenVerificationResult
from app.models.autenticacao import User


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
