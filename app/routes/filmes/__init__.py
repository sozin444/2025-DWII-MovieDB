from logging import exception

from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
import json

from app.forms.filmes import AvaliacaoForm, FilmeCrudForm, FilmeDeleteForm
from app.infra.modulos import db
from app.models.filme import Filme
from app.services.filme_service import FilmeService, FilmeServiceError
from app.services.imageprocessing_service import ImageProcessingService
from app.services.review_service import ReviewOperationResult, ReviewService

filme_bp = Blueprint(name='filme',
                     import_name=__name__,
                     url_prefix='/filme',
                     template_folder="templates", )


# Funções auxiliares para operações CRUD de filmes

def _preparar_form_data_filme(form: FilmeCrudForm) -> dict:
    """Extrai e prepara dados do formulário de filme para o serviço.

    Args:
        form: Formulário de filme validado

    Returns:
        dict: Dicionário com dados do filme prontos para o serviço
    """
    form_data = {
        'titulo_original': form.titulo_original.data,
        'titulo_portugues': form.titulo_portugues.data,
        'ano_lancamento': form.ano_lancamento.data,
        'lancado': form.lancado.data,
        'duracao_minutos': form.duracao_minutos.data,
        'sinopse': form.sinopse.data,
        'orcamento_milhares': form.orcamento_milhares.data,
        'faturamento_lancamento_milhares': form.faturamento_lancamento_milhares.data,
        'trailer_youtube': form.trailer_youtube.data,
        'poster': form.poster.data,
        'generos_selecionados': []
    }

    # Processar IDs de gêneros do campo oculto
    try:
        genero_ids_str = form.generos_selecionados.data or '[]'
        genero_ids = json.loads(genero_ids_str)
        form_data['generos_selecionados'] = genero_ids
    except (json.JSONDecodeError, TypeError):
        form_data['generos_selecionados'] = []

    return form_data


def _processar_resultado_filme(result: 'FilmeOperationResult', success_url: str):
    """Processa resultado da operação de filme e exibe mensagens apropriadas.

    Args:
        result: Resultado da operação do FilmeService
        success_url: URL para redirecionamento em caso de sucesso

    Returns:
        flask.Response: Redirecionamento para a URL apropriada
    """
    if result.success:
        flash(result.message, category='success')
        return redirect(success_url)
    else:
        flash(result.message, category='error')
        if result.errors:
            for field, errors in result.errors.items():
                flash(f"Erro no campo {field}: {errors}", category='error')
        return None


@filme_bp.route('/random', methods=['GET'])
def random_filme():
    """Apresenta um filme aleatório do banco de dados.

    Returns:
        Template renderizado com o filme
    """
    # Retorna apenas os dados do Filme, sem dados relacionados (joined)
    filme = db.session.scalar(select(Filme).order_by(func.random()))
    elenco = FilmeService.obter_elenco(filme)
    equipe_tecnica = FilmeService.obter_equipe_tecnica(filme)
    estatisticas = FilmeService.obter_estatisticas_avaliacoes(filme)

    # Buscar avaliação do usuário atual (se autenticado)
    avaliacao_usuario = None
    if current_user.is_authenticated:
        avaliacao_usuario = ReviewService.obter_avaliacao_usuario(filme, current_user)

    # Inicializar formulário de avaliação
    form = AvaliacaoForm()

    # Preencher formulário com dados existentes apenas em GET
    if request.method == 'GET' and avaliacao_usuario:
        # Definir os valores diretamente nos campos
        form.nota.data = avaliacao_usuario.nota
        form.comentario.data = avaliacao_usuario.comentario
        form.recomendaria.data = avaliacao_usuario.recomendaria

    # Buscar todas as avaliações do filme
    avaliacoes = ReviewService.obter_avaliacoes_filme(filme)

    return render_template('filme/web/details.jinja2',
                           title=f"Detalhes de '{filme.titulo_portugues}'",
                           elenco=elenco,
                           equipe_tecnica=equipe_tecnica,
                           estatisticas=estatisticas,
                           filme=filme,
                           form=form,
                           avaliacao_usuario=avaliacao_usuario,
                           avaliacoes=avaliacoes)


@filme_bp.route('/<uuid:filme_id>/avaliar', methods=['POST'])
@login_required
def avaliar_filme(filme_id):
    """Cria ou atualiza uma avaliação do filme pelo usuário atual.

    Args:
        filme_id (uuid.UUID): ID do filme a ser avaliado.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = AvaliacaoForm()

    if form.validate_on_submit():
        # Usar o ReviewService para criar/atualizar a avaliação
        resultado = ReviewService.criar_ou_atualizar_avaliacao(
                filme=filme,
                usuario=current_user,
                nota=form.nota.data,
                comentario=form.comentario.data or None,
                recomendaria=form.recomendaria.data
        )

        # Processar resultado
        if resultado.status in [ReviewOperationResult.CREATED, ReviewOperationResult.UPDATED]:
            flash(resultado.message, category='success')
        else:
            flash(resultado.message, category='error')

            # Mostrar erros específicos se houver
            if resultado.errors:
                for field, errors in resultado.errors.items():
                    for error in errors:
                        flash(f"Erro no campo {field}: {error}", category='error')
    else:
        # Mostrar erros de validação do formulário
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo {field}: {error}", category='error')

    # Redireciona para a página de detalhes do mesmo filme
    return redirect(url_for('filme.detail_filme', filme_id=filme_id))


@filme_bp.route('/avaliacao/<uuid:avaliacao_id>/excluir', methods=['POST'])
@login_required
def excluir_avaliacao(avaliacao_id):
    """Exclui uma avaliação do usuário atual.

    Args:
        avaliacao_id (uuid.UUID): ID da avaliação a ser excluída.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    # Busca a avaliação antes de excluir para obter o filme_id
    from app.models.juncoes import Avaliacao
    try:
        avaliacao = Avaliacao.get_by_id(avaliacao_id, raise_if_not_found=True)
        filme_id = avaliacao.filme_id
    except Avaliacao.RecordNotFoundError:
        flash("Avaliação não encontrada.", category='error')
        return redirect(url_for('filme.listar_filmes'))

    # Usar o ReviewService para excluir a avaliação
    resultado = ReviewService.excluir_avaliacao(avaliacao_id, current_user)

    # Processar resultado
    if resultado.status == ReviewOperationResult.DELETED:
        flash(resultado.message, category='success')
    else:
        flash(resultado.message, category='error')

    # Redireciona para a página de detalhes do mesmo filme
    return redirect(url_for('filme.detail_filme', filme_id=filme_id))


@filme_bp.route('/<uuid:filme_id>/poster', methods=['GET'])
def filme_poster(filme_id):
    """Serve o poster do filme

    Args:
        filme_id (uuid.UUID): ID do filme.

    Returns:
        flask.Response: Imagem do poster ou placeholder.
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        # Filme não encontrado - retorna placeholder
        poster_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                                    "Filme\nnão encontrado",
                                                                    36)
        mime_type = 'image/png'
    else:
        poster_data, mime_type = filme.poster
    return ImageProcessingService.servir_imagem(poster_data, mime_type)


@filme_bp.route('/<uuid:filme_id>/detail', methods=['GET'])
def detail_filme(filme_id):
    """Apresenta um filme do banco de dados.

    Returns:
        Template renderizado com o filme
    """
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        abort(404)

    # Retorna apenas os dados do Filme, sem dados relacionados (joined)
    elenco = FilmeService.obter_elenco(filme)
    equipe_tecnica = FilmeService.obter_equipe_tecnica(filme)
    estatisticas = FilmeService.obter_estatisticas_avaliacoes(filme)

    # Buscar avaliação do usuário atual (se autenticado)
    avaliacao_usuario = None
    if current_user.is_authenticated:
        avaliacao_usuario = ReviewService.obter_avaliacao_usuario(filme, current_user)

    # Inicializar formulário de avaliação
    form = AvaliacaoForm()

    # Preencher formulário com dados existentes apenas em GET
    if request.method == 'GET' and avaliacao_usuario:
        # Definir os valores diretamente nos campos
        form.nota.data = avaliacao_usuario.nota
        form.comentario.data = avaliacao_usuario.comentario
        form.recomendaria.data = avaliacao_usuario.recomendaria

    # Buscar todas as avaliações do filme
    avaliacoes = ReviewService.obter_avaliacoes_filme(filme)

    return render_template('filme/web/details.jinja2',
                           title=f"Detalhes de '{filme.titulo_portugues}'",
                           elenco=elenco,
                           equipe_tecnica=equipe_tecnica,
                           estatisticas=estatisticas,
                           filme=filme,
                           form=form,
                           avaliacao_usuario=avaliacao_usuario,
                           avaliacoes=avaliacoes)


@filme_bp.route('/', methods=['GET'])
def listar_filmes():
    """Apresenta um mosaico de posteres de filmes com link para detalhes do filme

    Returns:
        Template renderizado com mosaico de posteres paginados
    """
    from sqlalchemy import func
    
    # Aplicar ordenação aleatória na query
    # Como o CrudService não suporta func.random(), vamos fazer uma query customizada
    stmt = select(Filme).order_by(func.random()).limit(24)
    filmes = db.session.execute(stmt).scalars().all()
    
    # Calcular estatísticas para cada filme
    filmes_com_stats = []
    for filme in filmes:
        stats = FilmeService.obter_estatisticas_avaliacoes(filme)
        filmes_com_stats.append({
            'filme': filme,
            'stats': stats
        })
    
    return render_template('filme/web/lista.jinja2',
                           title="Lista de Filmes",
                           filmes_com_stats=filmes_com_stats)


@filme_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_filme():
    """Trata requisição GET para exibir formulário de criação e POST para processar submissão.

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    form = FilmeCrudForm()

    if request.method == 'POST':
        # Cuida do botão de cancelamento
        if form.cancel.data:
            return redirect(url_for('filme.listar_filmes'))

        if form.validate_on_submit():
            try:
                # Preparar dados do formulário usando função auxiliar
                form_data = _preparar_form_data_filme(form)

                # Criar filme usando o serviço
                result = FilmeService.create_filme(form_data)

                # Processar resultado usando função auxiliar
                response = _processar_resultado_filme(
                    result,
                    url_for('filme.detail_filme', filme_id=result.filme.id) if result.success else None
                )
                if response:
                    return response

            except FilmeServiceError as e:
                flash(f"Erro ao criar filme: {str(e)}", category='error')
            except Exception as e:
                flash("Erro interno do sistema. Tente novamente.", category='error')
        else:
            # Mostrar erros de validação do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/create.jinja2',
                           title="Criar Novo Filme",
                           form=form)


@filme_bp.route('/<uuid:filme_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_filme(filme_id):
    """Trata requisição GET para exibir formulário pré-populado de edição e POST para processar atualizações.

    Args:
        filme_id (uuid.UUID): ID do filme a ser editado

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    # Verificar existência do filme e tratar casos 404
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = FilmeCrudForm(obj=filme)

    if request.method == 'GET':
        # Pre-popula os campos do formulário
        form.titulo_original.data = filme.titulo_original
        form.titulo_portugues.data = filme.titulo_portugues
        form.ano_lancamento.data = filme.ano_lancamento
        form.lancado.data = filme.lancado
        form.duracao_minutos.data = filme.duracao_minutos
        form.sinopse.data = filme.sinopse
        form.orcamento_milhares.data = filme.orcamento_milhares
        form.faturamento_lancamento_milhares.data = filme.faturamento_lancamento_milhares
        form.trailer_youtube.data = filme.trailer_youtube

        # Pre-popula seleção de gêneros
        genero_ids = FilmeService.obter_genero_ids(filme)
        form.generos_selecionados.data = json.dumps(genero_ids)

    elif request.method == 'POST':
        # Cuida do botão de cancelamento
        if form.cancel.data:
            return redirect(url_for('filme.detail_filme', filme_id=filme_id))

        if form.validate_on_submit():
            try:
                # Preparar dados do formulário usando função auxiliar
                form_data = _preparar_form_data_filme(form)

                # Atualizar filme usando o serviço
                result = FilmeService.update_filme(filme_id, form_data)

                # Processar resultado usando função auxiliar
                response = _processar_resultado_filme(
                    result,
                    url_for('filme.detail_filme', filme_id=filme_id)
                )
                if response:
                    return response

            except FilmeServiceError as e:
                flash(f"Erro ao atualizar filme: {str(e)}", category='error')
            except Exception as e:
                flash("Erro interno do sistema. Tente novamente.", category='error')
        else:
            # Mostrar erros de validação do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/edit.jinja2',
                           title=f"Editar '{filme.titulo_original}'",
                           form=form,
                           filme=filme)


@filme_bp.route('/<uuid:filme_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_filme(filme_id):
    """Trata requisição GET para exibir confirmação de exclusão e POST para processar a exclusão.

    Args:
        filme_id (uuid.UUID): ID do filme a ser excluído

    Returns:
        flask.Response: Template renderizado para GET ou redirecionamento para POST bem-sucedido
    """
    # Validate filme existence and handle 404 cases
    try:
        filme = Filme.get_by_id(filme_id,
                                raise_if_not_found=True)
    except Filme.RecordNotFoundError:
        flash("Filme não encontrado.", category='error')
        abort(404)

    form = FilmeDeleteForm(obj=filme)

    if request.method == 'POST':
        # Handle cancel button
        if form.cancel.data:
            return redirect(url_for('filme.detail_filme', filme_id=filme_id))

        if form.validate_on_submit():
            try:
                # Delete filme using service
                result = FilmeService.delete_filme(filme_id)

                if result.success:
                    flash(result.message, category='success')
                    return redirect(url_for('filme.listar_filmes'))
                else:
                    flash(result.message, category='error')
                    if result.errors:
                        for field, errors in result.errors.items():
                            flash(f"Erro no campo {field}: {errors}", category='error')

            except FilmeServiceError as e:
                flash(f"Erro ao excluir filme: {str(e)}", category='error')
            except Exception as e:
                flash("Erro interno do sistema. Tente novamente.", category='error')
        else:
            # Show form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Erro no campo {field}: {error}", category='error')

    return render_template('filme/web/delete.jinja2',
                           title=f"Excluir '{filme.titulo_original}'",
                           form=form,
                           filme=filme)
