import uuid
from datetime import datetime
from pydoc import pager
from urllib.parse import urlsplit

from werkzeug.exceptions import NotFound

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, \
    url_for
from flask_login import current_user, fresh_login_required, login_required
from markupsafe import Markup

from app import anonymous_required
from app.forms.auth import AskToResetPasswordForm, LoginForm, ProfileForm, Read2FACodeForm, \
    RegistrationForm, \
    SetNewPasswordForm
from app.forms.generos import GeneroEditForm
from app.models.filme import Genero
from app.services.backup2fa_service import Backup2FAService
from app.services.imageprocessing_service import ImageProcessingService
from app.services.user_2fa_service import Autenticacao2FA, User2FAService
from app.services.user_service import UserOperationStatus, UserService
from app.infra.modulos import db


genero_bp = Blueprint(name='genero',
                      import_name=__name__,
                      url_prefix='/genero',
                      template_folder="templates", )

@genero_bp.route('/', methods=['GET'])
def listar_generos():
    MAX_PER_PAGE = int(current_app.config.get('MAX_PER_PAGE', 500))

    page = request.args.get('page', default=1, type=int)
    pp = request.args.get('pp', default=50, type=int)
    q = request.args.get('q', default=None, type=str)
    a = request.args.get('a', default=0, type=int)

    if pp > MAX_PER_PAGE:
        pp = MAX_PER_PAGE

    sentenca = db.select(Genero)

    # Filtrar por parte do nome
    if q is not None:
        sentenca = sentenca.filter(Genero.nome.ilike(f"%{q}%"))

    # Filtrar por ativos/inativos
    match a:
        case 1:
            sentenca = sentenca.filter_by(ativo=True)
        case 2:
            sentenca = sentenca.filter_by(ativo=False)
        case _:
            pass

    sentenca = sentenca.order_by(Genero.nome)

    try:
        rset_page = db.paginate(sentenca, page=page, per_page=pp, max_per_page=MAX_PER_PAGE,
                                error_out=True)
    except NotFound as e:
        current_app.logger.warning(f"Exception: {e}")
        page = 1
        flash("Não existem registros na página solicitada. Apresentando primeira página",
              category='info')
        rset_page = db.paginate(sentenca, page=page, per_page=pp, max_per_page=MAX_PER_PAGE,
                                error_out=True)

    return render_template('genero/web/lista.jinja2',
                           title="Lista de gêneros",
                           rset_page=rset_page,
                           page=page,
                           q=q,
                           pp=pp,
                           a=a)

@genero_bp.route('/<uuid:genero_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_genero(genero_id: uuid.UUID):
    genero: Genero = Genero.get_by_id(genero_id)
    if genero is None:
        flash("Gênero não encontrado.", category='warning')
        return redirect(url_for('generos.listar_generos'))

    numero_de_filmes = len(genero.filmes)

    form = GeneroEditForm()
    if request.method == 'GET':
        # Preenche o formulário com os dados atuais do gênero
        form.nome.data = genero.nome
        form.ativo.data = genero.ativo
        form.descricao.data = genero.descricao

    if form.validate_on_submit():
        # Atualiza os campos do gênero usando os dados do formulário WTForms
        genero.nome = form.nome.data.strip()
        genero.ativo = form.ativo.data
        genero.descricao = form.descricao.data

        # Salva as alterações no banco de dados
        try:
            db.session.commit()
            flash("Gênero atualizado com sucesso.", category='success')
            return redirect(url_for('genero.listar_generos'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar gênero: {e}")
            flash("Ocorreu um erro ao atualizar o gênero. Tente novamente.", category='danger')

    return render_template('genero/web/editar.jinja2',
                           title="Editar gênero",
                           form=form,
                           numero_de_filmes=numero_de_filmes)
