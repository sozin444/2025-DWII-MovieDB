import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.models.mixins import AuditMixin, BasicRepositoryMixin

if TYPE_CHECKING:  # Para type checking e evitar importações circulares
    from app.models.juncoes import Atuacao, EquipeTecnica  # noqa: F401
    from app.models.filme import FuncaoTecnica  # noqa: F401


class Pessoa(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'pessoas'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(100))
    data_nascimento: Mapped[Optional[datetime]] = mapped_column(Date, default=None)
    local_nascimento: Mapped[Optional[str]] = mapped_column(String(100))
    biografia: Mapped[Optional[str]] = mapped_column(Text)
    foto_base64: Mapped[Optional[str]] = mapped_column(Text)
    foto_mime: Mapped[Optional[str]] = mapped_column(String(129))
    com_foto: Mapped[bool] = mapped_column(default=False, server_default='false')

    ator: Mapped[Optional["Ator"]] = relationship(back_populates="pessoa",
                                                  cascade="all, delete-orphan")

    funcoes_tecnicas: Mapped[list["EquipeTecnica"]] = relationship(
            back_populates="pessoa",
            cascade="all, delete-orphan",
            overlaps="funcoes_tecnicas_executadas,pessoas_executando,pessoas")

    funcoes_tecnicas_executadas: Mapped[list["FuncaoTecnica"]] = relationship(
            secondary="equipes_tecnicas",
            back_populates="pessoas",
            overlaps="funcoes_tecnicas,pessoas_executando")


class Ator(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'atores'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('pessoas.id',
                                                            ondelete="CASCADE"),
                                                 unique=True)
    nome_artistico: Mapped[Optional[str]] = mapped_column(String(100))

    pessoa: Mapped["Pessoa"] = relationship(back_populates="ator")
    filmes: Mapped[list["Atuacao"]] = relationship(back_populates="ator",
                                                   cascade="all, delete-orphan")
