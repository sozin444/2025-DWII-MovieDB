from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from ..models.autenticacao import User


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
    status: UserOperationStatus
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
                          session=None,
                          auto_commit: bool = True) -> UserRegistrationResult:
        """Registra um novo usuário no sistema.

        Args:
            nome (str): Nome completo do usuário
            email (str): Email do usuário (será normalizado)
            password (str): Senha em texto plano (será hasheada)
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
            usuario.password = password  # Será hasheado pelo setter


            session.add(usuario)
            session.flush()
            session.refresh(usuario)

            cls.confirmar_email(usuario,
                                session=session,
                                auto_commit=False)

            if auto_commit:
                session.commit()
                current_app.logger.info("Usuário registrado: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Usuário marcado para registro (sem commit): %s" % (usuario.email,))

            return UserRegistrationResult(
                    status=UserOperationStatus.SUCCESS,
                    user=usuario
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
    def confirmar_email(cls,
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
                        "Tentativa de confirmar email já confirmado: %s" % (usuario.email,))
                return True  # Já está confirmado, não é erro

            usuario.ativo = True
            usuario.dta_validacao_email = datetime.now()

            if auto_commit:
                session.commit()
                current_app.logger.info("Email confirmado para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Email marcado para confirmação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao confirmar email do usuário %s: %s" % (usuario.email, str(e)))
            raise e

    @classmethod
    def desconfirmar_email(cls,
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
                        "Tentativa de desconfirmar email não confirmado: %s" % (usuario.email,))
                return True  # Não está confirmado, não é erro

            usuario.ativo = False
            usuario.dta_validacao_email = None

            if auto_commit:
                session.commit()
                current_app.logger.info("Email desconfirmado para usuário: %s" % (usuario.email,))
            else:
                current_app.logger.debug(
                        "Email marcado para desconfirmação (sem commit): %s" % (usuario.email,))

            return True

        except SQLAlchemyError as e:
            if auto_commit:
                session.rollback()
            current_app.logger.error(
                    "Erro ao desconfirmar email do usuário %s: %s" % (usuario.email, str(e)))
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
