"""Serviço de gerenciamento de filmes.

Este módulo fornece a camada de serviço para operações relacionadas a filmes,
incluindo cálculo de estatísticas, avaliações, e outras operações de negócio.

Classes principais:
    - FilmeService: Serviço principal com métodos para operações de filmes
"""
from dataclasses import dataclass

from sqlalchemy import desc, func, Integer, select

from app.infra.modulos import db
from app.models.filme import Filme
from .utils import aplicar_filtro_creditado


@dataclass
class FilmeReviewStats:
    nota_media: float
    total_avaliacoes: int
    total_recomendacoes: int
    percentual_recomendacoes: float
    distribuicao_notas: dict[int, float]  # {nota: percentual}


class FilmeService:
    """Serviço para operações relacionadas a filmes.

    Centraliza a lógica de negócio relacionada a filmes, separando-a dos modelos.
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
    def obter_estatisticas_avaliacoes(cls,
                                      filme: Filme,
                                      session=None) -> FilmeReviewStats:
        """Retorna estatísticas de avaliações do filme.

        Args:
            filme (Filme): Instância do filme para calcular estatísticas
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            FilmeReviewStats: Objeto contendo estatísticas de avaliações do filme
        """
        from app.models.juncoes import Avaliacao

        if session is None:
            session = cls._default_session

        # Query para agregar estatísticas das avaliações
        stmt = select(
                func.avg(Avaliacao.nota).label('nota_media'),
                func.count(Avaliacao.id).label('total_avaliacoes'),
                func.sum(func.cast(Avaliacao.recomendaria, Integer)).label('total_recomendacoes')
        ).where(Avaliacao.filme_id == filme.id)

        resultado = session.execute(stmt).one()

        # Extrai os valores do resultado
        nota_media = float(resultado.nota_media) if resultado.nota_media is not None else 0.0
        total_avaliacoes = int(
            resultado.total_avaliacoes) if resultado.total_avaliacoes is not None else 0
        total_recomendacoes = int(
            resultado.total_recomendacoes) if resultado.total_recomendacoes is not None else 0

        # Calcula percentual de recomendações
        percentual_recomendacoes = (
                    total_recomendacoes / total_avaliacoes * 100) if total_avaliacoes > 0 else 0.0

        # Calcula distribuição de notas (0 a 10)
        distribuicao_notas = {}
        if total_avaliacoes > 0:
            # Query para contar avaliações por nota
            stmt_distribuicao = select(
                Avaliacao.nota,
                func.count(Avaliacao.id).label('count')
            ).where(Avaliacao.filme_id == filme.id).group_by(Avaliacao.nota)
            
            resultado_distribuicao = session.execute(stmt_distribuicao).all()
            
            # Inicializa todas as notas com 0%
            for nota in range(0, 11):
                distribuicao_notas[nota] = 0.0
            
            # Calcula percentuais para notas que existem
            for row in resultado_distribuicao:
                nota = row.nota
                count = row.count
                percentual = (count / total_avaliacoes * 100)
                distribuicao_notas[nota] = round(percentual, 2)
        else:
            # Se não há avaliações, todas as notas têm 0%
            for nota in range(0, 11):
                distribuicao_notas[nota] = 0.0

        return FilmeReviewStats(nota_media=round(nota_media, 2),
                                total_avaliacoes=total_avaliacoes,
                                total_recomendacoes=total_recomendacoes,
                                percentual_recomendacoes=round(percentual_recomendacoes, 2),
                                distribuicao_notas=distribuicao_notas)

    @classmethod
    def obter_elenco(cls,
                     filme: Filme,
                     creditado: bool = True,
                     nao_creditado: bool = True,
                     usar_nome_artistico: bool =True,
                     session=None) -> list:
        """Retorna lista de atores e personagens do filme.

        Args:
            filme (Filme): Instância do filme
            creditado (bool): Se True, inclui atuações creditadas. Default: True
            nao_creditado (bool): Se True, inclui atuações não creditadas. Default: True
            usar_nome_artistico (bool): Se True, usa o nome artístico do ator se disponível.
                                        Caso contrário, usa o nome real. Default: True
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de tuplas com estrutura:
                [
                    ('Christian Bale', 'Batman', True, 21040b96-4794-41a7-9253-f135743ce482),         # (nome_ator, personagem, creditado, id_ator)
                    ('Christian Bale', 'Bruce Wayne', True, 21040b96-4794-41a7-9253-f135743ce482),
                    ('Debbi Burns', 'Bank Patron', False, 5c3f1e2e-3f4e-4d2a-9f4b-2e5f6c7d8e9f),
                    ...
                ]
                Ordenada por tempo_de_tela_minutos (decrescente) + ordem alfabética do nome.
                Se um ator interpreta múltiplos personagens, aparece múltiplas vezes.
                Retorna lista vazia se nenhum dos filtros estiver ativo.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Apenas elenco creditado
            >>> FilmeService.obter_elenco(filme,nao_creditado=False)

            >>> # Apenas elenco não creditado
            >>> FilmeService.obter_elenco(filme,creditado=False)

            >>> # Elenco completo
            >>> FilmeService.obter_elenco(filme)
        """
        from app.models.juncoes import Atuacao
        from app.models.pessoa import Ator, Pessoa

        if session is None:
            session = cls._default_session

        # Constrói a query base com joins para acessar o nome do ator
        stmt = select(Atuacao). \
            join(Atuacao.ator). \
            join(Ator.pessoa). \
            where(Atuacao.filme_id == filme.id)

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, Atuacao.creditado, creditado, nao_creditado)

        # Ordena por tempo de tela (decrescente) e depois por nome alfabético
        stmt = stmt.order_by(desc(Atuacao.tempo_de_tela_minutos), Pessoa.nome)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Monta a lista de tuplas (nome_ator, personagem, creditado)
        elenco = [
            (atuacao.ator.nome_artistico if usar_nome_artistico and atuacao.ator.nome_artistico else atuacao.ator.pessoa.nome,
             atuacao.personagem,
             atuacao.creditado,
             atuacao.ator.pessoa.id)
            for atuacao in resultado
        ]

        return elenco

    @classmethod
    def obter_equipe_tecnica(cls,
                             filme: Filme,
                             creditado: bool = True,
                             nao_creditado: bool = True,
                             funcoes: list = None,
                             session=None) -> list:
        """Retorna lista de pessoas e funções técnicas da equipe do filme.

        Args:
            filme (Filme): Instância do filme
            creditado (bool): Se True, inclui funções creditadas. Default: True
            nao_creditado (bool): Se True, inclui funções não creditadas. Default: True
            funcoes (list[FuncaoTecnica]): Lista opcional de funções técnicas para filtrar.
                                          Se None, retorna todas as funções. Default: None
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de tuplas com estrutura:
                [
                    ('Diretor', 'Christopher Nolan', True, d3ebd0ba-f5e9-412f-8f4a-4c21e1cd5ff1),    # (nome_funcao, nome_pessoa, creditado, id_pessoa)
                    ('Produtor', 'Emma Thomas', True, 7a1c2e3d-8f4b-4c5d-9e6f-1a2b3c4d5e6f),
                    ('Roteirista', 'Christopher Nolan', True, d3ebd0ba-f5e9-412f-8f4a-4c21e1cd5ff1),
                    ...
                ]
                Ordenada por nome da função (alfabética).
                Se uma pessoa tem múltiplas funções, aparece múltiplas vezes.
                Retorna lista vazia se nenhum dos filtros estiver ativo.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Toda a equipe técnica
            >>> FilmeService.obter_equipe_tecnica(filme)

            >>> # Apenas equipe creditada
            >>> FilmeService.obter_equipe_tecnica(filme, nao_creditado=False)

            >>> # Apenas diretores e roteiristas
            >>> diretor = FuncaoTecnica.query.filter_by(nome='Diretor').first()
            >>> roteirista = FuncaoTecnica.query.filter_by(nome='Roteirista').first()
            >>> FilmeService.obter_equipe_tecnica(filme, funcoes=[diretor, roteirista])
        """
        from app.models.juncoes import EquipeTecnica
        from app.models.filme import FuncaoTecnica

        if session is None:
            session = cls._default_session

        # Constrói a query base com joins para acessar nome da pessoa e da função
        stmt = select(EquipeTecnica). \
            join(EquipeTecnica.pessoa). \
            join(EquipeTecnica.funcao_tecnica). \
            where(EquipeTecnica.filme_id == filme.id)

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, EquipeTecnica.creditado, creditado, nao_creditado)

        # Aplica filtro de funções específicas, se fornecido
        if funcoes is not None and len(funcoes) > 0:
            funcoes_ids = [funcao.id_pessoa for funcao in funcoes]
            stmt = stmt.where(EquipeTecnica.funcao_tecnica_id.in_(funcoes_ids))

        # Ordena por nome da função (alfabético)
        stmt = stmt.order_by(FuncaoTecnica.nome)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Monta a lista de tuplas (nome_funcao, nome_pessoa, creditado, id_pessoa)
        equipe = [
            (equipe_membro.funcao_tecnica.nome,
             equipe_membro.pessoa.nome,
             equipe_membro.creditado,
             equipe_membro.pessoa.id)
            for equipe_membro in resultado
        ]

        return equipe
