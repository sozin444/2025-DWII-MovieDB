from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.forms.filmes import AvaliacaoForm
from app.infra.modulos import db
from app.models.filme import Filme
from app.services.filme_service import FilmeService
from app.services.imageprocessing_service import ImageProcessingService
from app.services.review_service import ReviewOperationResult, ReviewService

filme_bp = Blueprint(name='filme',
                     import_name=__name__,
                     url_prefix='/filme',
                     template_folder="templates", )


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

    return render_template('filme/web/random.jinja2',
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
    filme = Filme.get_by_id(filme_id)
    if not filme:
        flash("Filme não encontrado.", category='error')
        return redirect(url_for('filme.random_filme'))

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

    return redirect(url_for('filme.random_filme'))


@filme_bp.route('/avaliacao/<uuid:avaliacao_id>/excluir', methods=['POST'])
@login_required
def excluir_avaliacao(avaliacao_id):
    """Exclui uma avaliação do usuário atual.

    Args:
        avaliacao_id (uuid.UUID): ID da avaliação a ser excluída.

    Returns:
        flask.Response: Redireciona de volta para a página do filme.
    """
    # Usar o ReviewService para excluir a avaliação
    resultado = ReviewService.excluir_avaliacao(avaliacao_id, current_user)

    # Processar resultado
    if resultado.status == ReviewOperationResult.DELETED:
        flash(resultado.message, category='success')
    else:
        flash(resultado.message, category='error')

    return redirect(url_for('filme.random_filme'))


@filme_bp.route('/<uuid:filme_id>/poster', methods=['GET'])
def filme_poster(filme_id):
    """Serve o poster do filme

    Args:
        filme_id (uuid.UUID): ID do filme.

    Returns:
        flask.Response: Imagem do poster ou placeholder.
    """
    filme = Filme.get_by_id(filme_id)

    if filme:
        poster_data, mime_type = filme.poster
        return ImageProcessingService.servir_imagem(poster_data, mime_type)
    else:
        # Usuário não encontrado - retorna placeholder
        placeholder_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                                    "Filme\nnão encontrado",
                                                                    36)
        return ImageProcessingService.servir_imagem(placeholder_data, 'image/png')


@filme_bp.route('/<uuid:filme_id>/detail', methods=['GET'])
def detail_filme(filme_id):
    """Apresenta um filme do banco de dados.

    Returns:
        Template renderizado com o filme
    """

    filme = Filme.get_by_id(filme_id)

    if not filme:
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

    return render_template('filme/web/random.jinja2',
                           title=f"Detalhes de '{filme.titulo_portugues}'",
                           elenco=elenco,
                           equipe_tecnica=equipe_tecnica,
                           estatisticas=estatisticas,
                           filme=filme,
                           form=form,
                           avaliacao_usuario=avaliacao_usuario,
                           avaliacoes=avaliacoes)
