import decimal
import uuid
from base64 import b64decode
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.modulos import db
from app.models.mixins import AuditMixin, BasicRepositoryMixin
from app.services.imageprocessing_service import ImageProcessingError, ImageProcessingService

if TYPE_CHECKING:  # Para type checking e evitar importações circulares
    from app.models.juncoes import FilmeGenero, Atuacao, EquipeTecnica, Avaliacao  # noqa: F401
    from app.models.autenticacao import User  # noqa: F401


class Filme(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'filmes'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    titulo_original: Mapped[str] = mapped_column(String(180))
    titulo_portugues: Mapped[Optional[str]] = mapped_column(String(180))
    ano_lancamento: Mapped[Optional[int]] = mapped_column()
    lancado: Mapped[bool] = mapped_column(default=False, server_default='false')
    duracao_minutos: Mapped[Optional[int]] = mapped_column()
    sinopse: Mapped[Optional[str]] = mapped_column(Text)
    orcamento_milhares: Mapped[Optional[decimal.Decimal]] = mapped_column(DECIMAL(10, 2))
    faturamento_lancamento_milhares: Mapped[Optional[decimal.Decimal]] = mapped_column(
            DECIMAL(10, 2))
    com_poster: Mapped[bool] = mapped_column(default=False, server_default='false')
    poster_base64: Mapped[Optional[str]] = mapped_column(Text)
    poster_mime: Mapped[Optional[str]] = mapped_column(String(129))
    trailer_youtube: Mapped[Optional[str]] = mapped_column(String(255))

    # Relacionamentos: um filme pode ter vários gêneros (via tabela de associação)
    filme_generos: Mapped[list["FilmeGenero"]] = relationship(back_populates="filme",
                                                              cascade="all, delete-orphan")
    generos: Mapped[list["Genero"]] = relationship(secondary="filmes_generos",
                                                   back_populates="filmes",
                                                   overlaps="filme_generos")

    elenco: Mapped[list["Atuacao"]] = relationship(back_populates="filme",
                                                   cascade="all, delete-orphan")
    equipe_tecnica: Mapped[list["EquipeTecnica"]] = relationship(back_populates="filme",
                                                                 cascade="all, delete-orphan")

    # Relacionamento: um filme pode ser avaliado por vários usuários
    avaliacoes: Mapped[list["Avaliacao"]] = relationship(back_populates="filme",
                                                         cascade="all, delete-orphan")

    @property
    def duracao_formatada(self) -> str:
        """Retorna a duração do filme formatada como string.

        Returns:
            str: Duração no formato "XhYmin" (ex: "1h45min", "2h15min")
        """
        horas = self.duracao_minutos // 60
        minutos = self.duracao_minutos % 60
        return f"{horas}h{minutos:02d}min"

    @property
    def listar_nomes_generos(self) -> list[str]:
        """
        Retorna uma lista com os nomes dos gêneros associados a este filme.
        """
        return sorted(genero.nome for genero in self.generos)

    @property
    def poster(self) -> tuple[bytes, str]:
        """Retorna o poster do filme em bytes e o tipo MIME.

        Se o filme não possuir um poster, retorna um placeholder.

        Returns:
            tuple[bytes, str]: Tupla contendo os bytes do poster e o tipo MIME.
                Sempre retorna uma imagem (poster ou placeholder).
        """
        if self.com_poster:
            data = b64decode(str(self.poster_base64))
            mime_type = self.poster_mime
        else:
            data = b64decode(ImageProcessingService.gerar_placeholder(200, 300))
            mime_type = 'image/png'
        return data, mime_type

    @poster.setter
    def poster(self, value):
        """Setter para poster.

        Atualiza os campos relacionados ao poster. Se o valor for None, remove o
        psoter e limpa os campos associados. Caso contrário, tenta armazenar
        o poster em base64 e o tipo MIME.

        IMPORTANTE: Este setter NÃO realiza commit. O chamador é responsável por
        gerenciar a transação (commit/rollback).

        Args:
            value: Um objeto com métodos `read()` e atributo `mimetype`, ou None.

        Raises:
            ImageProcessingError: Se houver erro ao processar a imagem.
            ValueError: Se o valor fornecido for inválido.
        """
        if value is None:
            self._clear_poster_fields()
        else:
            try:
                resultado = ImageProcessingService.processar_upload_foto(value)
            except (ImageProcessingError, ValueError):
                self._clear_poster_fields()
                raise
            else:
                self.poster_base64 = resultado.imagem_base64
                self.poster_mime = resultado.mime_type
                self.com_poster = True

    def _clear_poster_fields(self):
        """Limpa os campos relacionados ao poster.

        Útil para operações internas onde o poster precisa ser removido
        sem passar pelo setter público.
        """
        self.poster_base64 = None
        self.poster_mime = None
        self.com_poster = False


class Genero(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'generos'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(40), unique=True)
    descricao: Mapped[Optional[str]] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(default=True, server_default='true')

    filme_generos: Mapped[list["FilmeGenero"]] = relationship(back_populates="genero",
                                                              cascade="all, delete-orphan",
                                                              overlaps="generos,filmes")
    filmes: Mapped[list["Filme"]] = relationship(secondary="filmes_generos",
                                                 back_populates="generos",
                                                 overlaps="filme_generos")


class FuncaoTecnica(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'funcoes_tecnicas'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    ativo: Mapped[bool] = mapped_column(default=True, server_default='true')

    pessoas_executando: Mapped[list["EquipeTecnica"]] = relationship(
            back_populates="funcao_tecnica",
            cascade="all, delete-orphan")
