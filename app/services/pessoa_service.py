"""Serviço de gerenciamento de pessoas.

Este módulo fornece a camada de serviço para operações relacionadas a pessoas,
incluindo consulta de funções técnicas em filmes e outras operações de negócio.

Classes principais:
    - PessoaService: Serviço principal com métodos para operações de pessoas
"""
from collections import defaultdict

from sqlalchemy import select

from app.infra.modulos import db
from app.models.pessoa import Pessoa
from .utils import aplicar_filtro_creditado


class PessoaService:
    """Serviço para operações relacionadas a pessoas.

    Centraliza a lógica de negócio relacionada a pessoas, separando-a dos modelos.
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
    def obter_funcoes(cls,
                      pessoa: Pessoa,
                      creditado: bool = True,
                      nao_creditado: bool = True,
                      year_reverse: bool = True,
                      session=None) -> list:
        """Retorna lista de filmes e funções técnicas desempenhadas pela pessoa.

        Args:
            pessoa (Pessoa): Instância da pessoa
            creditado (bool): Se True, inclui funções creditadas. Default: True
            nao_creditado (bool): Se True, inclui funções não creditadas. Default: True
            year_reverse (bool): Se True, ordena do filme mais recente para o mais antigo.
            Default: True
            session: Sessão SQLAlchemy opcional. Se None, usa a sessão padrão da classe.

        Returns:
            list: Lista de dicionários com estrutura:
                [
                    {
                        'filme': Filme,
                        'funcoes': [
                            ('Diretor', True),   # (nome_funcao, creditado)
                            ('Montador', False)
                        ]
                    },
                    ...
                ]
                Retorna lista vazia se nenhum dos filtros estiver ativo.
                A lista é ordenada por ano de lançamento do filme.

        Raises:
            ValueError: Se ambos os filtros forem False

        Examples:
            >>> # Apenas funções creditadas
            >>> PessoaService.obter_funcoes(pessoa, nao_creditado=False)

            >>> # Apenas funções não creditadas
            >>> PessoaService.obter_funcoes(pessoa, creditado=False)

            >>> # Todas as funções
            >>> PessoaService.obter_funcoes(pessoa)
        """
        from app.models.juncoes import EquipeTecnica
        from app.models.filme import Filme
        from sqlalchemy import desc

        if session is None:
            session = cls._default_session

        # Constrói a query base com join no Filme para ordenação
        stmt = select(EquipeTecnica). \
            join(Filme, EquipeTecnica.filme_id == Filme.id). \
            where(EquipeTecnica.pessoa_id == pessoa.id)
        if year_reverse:
            stmt = stmt.order_by(desc(Filme.ano_lancamento))
        else:
            stmt = stmt.order_by(Filme.ano_lancamento)

        # Aplica filtros de creditado usando função utilitária
        stmt = aplicar_filtro_creditado(stmt, EquipeTecnica.creditado, creditado, nao_creditado)

        # Executa a query
        resultado = session.execute(stmt).scalars().all()

        # Agrupa funções por filme
        filmes_funcoes = defaultdict(list)
        filmes_obj = {}  # Guarda referência aos objetos Filme

        for equipe in resultado:
            filme_id = equipe.filme_id
            # Adiciona tupla (nome_funcao, creditado)
            filmes_funcoes[filme_id].append((equipe.funcao_tecnica.nome, equipe.creditado))
            if filme_id not in filmes_obj:
                filmes_obj[filme_id] = equipe.filme

        # Monta a lista de retorno mantendo a ordem do resultado
        funcoes = []
        filmes_adicionados = set()
        for equipe in resultado:
            if equipe.filme_id not in filmes_adicionados:
                funcoes.append({
                    'filme'  : equipe.filme,
                    'funcoes': filmes_funcoes[equipe.filme_id]
                })
                filmes_adicionados.add(equipe.filme_id)

        return funcoes
