import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, select, String
from sqlalchemy.orm import Mapped, mapped_column

from app import db
from app.services.email_service import EmailValidationService
from .mixins import AuditMixin, BasicRepositoryMixin


class User(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    email_normalizado: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    ativo: Mapped[bool] = mapped_column(default=False, server_default='false')
    dta_validacao_email: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                    default=None)

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
        """Armazena o hash da senha do usuário.

        Args:
            value (str): Senha em texto plano a ser hashada e armazenada.
        """
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(value)

    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """Retorna o usuário com o e-mail especificado, ou None se não encontrado.

        Args:
            email (str): E-mail previamente normalizado que será buscado.

        Returns:
            typing.Optional[User]: O usuário encontrado, ou None.
        """
        return db.session.scalar(select(cls).where(User.email_normalizado == email))
