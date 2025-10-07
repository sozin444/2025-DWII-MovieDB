"""Módulo de modelos de autenticação.

Define o modelo User e funcionalidades relacionadas à autenticação de usuários,
incluindo gerenciamento de senhas, validação de email, e upload de fotos de perfil.

Classes principais:
    - User: Modelo principal de usuário com autenticação e perfil
"""
import uuid
from base64 import b64decode
from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import DateTime, select, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app import db
from app.services.email_service import EmailValidationService
from app.services.imageprocessing_service import ImageProcessingService
from .mixins import AuditMixin, BasicRepositoryMixin


class User(db.Model, BasicRepositoryMixin, AuditMixin, UserMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    email_normalizado: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    ativo: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_validacao_email: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                    default=None)
    dta_ultima_alteracao_senha: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                           default=None)

    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                             default=None)

    com_foto: Mapped[bool] = mapped_column(default=False, server_default='false')
    foto_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    avatar_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    foto_mime: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    @property
    def email(self):
        """Retorna o e-mail normalizado do usuário.

        Returns:
            str: E-mail normalizado do usuário.
        """
        return self.email_normalizado

    @email.setter
    def email(self, value):
        """Define e normaliza o e-mail do usuário.

        Args:
            value (str): E-mail a ser normalizado e armazenado.

        Raises:
            ValueError: Se o e-mail fornecido for inválido.
        """
        try:
            normalizado = EmailValidationService.normalize(value)
        except ValueError:
            raise ValueError(f"E-mail inválido: {value}")
        self.email_normalizado = normalizado

    @property
    def password(self):
        """Retorna o hash da senha do usuário.

        Returns:
            str: Hash da senha do usuário.
        """
        return self.password_hash

    @password.setter
    def password(self, value):
        """Armazena o hash da senha do usuário e registra a data de alteração.

        Args:
            value (str): Senha em texto plano a ser hashada e armazenada.
        """
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(value)
        self.dta_ultima_alteracao_senha = datetime.now()

    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """Retorna o usuário com o e-mail especificado, ou None se não encontrado.

        Args:
            email (str): E-mail previamente normalizado que será buscado.

        Returns:
            typing.Optional[User]: O usuário encontrado, ou None.
        """
        return db.session.scalar(select(cls).where(User.email_normalizado == email))

    @property
    def is_active(self):
        """Indica se o usuário está ativo.

        Returns:
            bool: True se o usuário está ativo, False caso contrário.
        """
        return self.ativo

    def get_id(self):
        """Retorna identificador único para o Flask-Login com invalidação automática de sessão.

        Implementa token alternativo combinando ID do usuário com parte do hash da senha.
        Quando a senha é alterada, o hash muda e todas as sessões anteriores são invalidadas
        automaticamente.

        Returns:
            str: String no formato "{user_id}|{últimos_15_chars_do_hash}".

        References:
            https://flask-login.readthedocs.io/en/latest/#alternative-tokens
        """
        return f"{str(self.id)}|{self.password[-15:]}"

    def check_password(self, password) -> bool:
        """Verifica se a senha fornecida corresponde ao hash armazenado.

        Args:
            password (str): Senha em texto plano a ser verificada.

        Returns:
            bool: True se a senha estiver correta, False caso contrário.
        """
        from werkzeug.security import check_password_hash
        return check_password_hash(str(self.password_hash), password)

    @property
    def foto(self) -> tuple[bytes | None, str | None]:
        """Retorna a foto original do usuário em bytes e o tipo MIME.

        Returns:
            tuple[bytes | None, str | None]: Tupla contendo os bytes da foto e o tipo MIME,
                ou (None, None) se o usuário não possui foto.
        """
        if self.com_foto:
            data = b64decode(str(self.foto_base64))
            mime_type = self.foto_mime
        else:
            data = None
            mime_type = None
        return data, mime_type

    @property
    def avatar(self) -> tuple[bytes | None, str | None]:
        """Retorna o avatar do usuário em bytes e o tipo MIME.

        Returns:
            tuple[bytes | None, str | None]: Tupla contendo os bytes do avatar e o tipo MIME,
                ou (None, None) se o usuário não possui foto.
        """
        if self.com_foto:
            data = b64decode(str(self.avatar_base64))
            mime_type = self.foto_mime
        else:
            data = None
            mime_type = None
        return data, mime_type

    @foto.setter
    def foto(self, value):
        """Setter para a foto/avatar do usuário.

        Atualiza os campos relacionados à foto do usuário. Se o valor for None,
        remove a foto e limpa os campos associados. Caso contrário, tenta armazenar
        a foto em base64 e o tipo MIME.

        IMPORTANTE: Este setter NÃO realiza commit. O chamador é responsável por
        gerenciar a transação (commit/rollback).

        Args:
            value: Um objeto com métodos `read()` e atributo `mimetype`, ou None.

        Raises:
            ImageProcessingError: Se houver erro ao processar a imagem.
            ValueError: Se o valor fornecido for inválido.
        """
        if value is None:
            self.com_foto = False
            self.foto_base64 = None
            self.avatar_base64 = None
            self.foto_mime = None
        else:
            resultado = ImageProcessingService.processar_upload_foto(value)
            self.foto_base64 = resultado.foto_base64
            self.avatar_base64 = resultado.avatar_base64
            self.foto_mime = resultado.mime_type
            self.com_foto = True
