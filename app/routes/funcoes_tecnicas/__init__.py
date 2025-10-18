import uuid

from werkzeug.exceptions import NotFound

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.forms.funcoes_tecnicas import FuncaoTecnicaEditForm
from app.models.filme import FuncaoTecnica
from app.infra.modulos import db


funcao_tecnica_bp = Blueprint(
    name='funcao_tecnica',
    import_name=__name__,
    url_prefix='/funcao_tecnica',
    template_folder="templates",
)


@funcao_tecnica_bp.route('/', methods=['GET'])
def listar_funcoes_tecnicas():
    """Lista todas as funções técnicas com suporte a filtros e paginação.

    Query Parameters:
        page (int): Número da página (padrão: 1)
        pp (int): Itens por página (padrão: 50, máximo: MAX_PER_PAGE)
        q (str): Filtro de busca parcial por nome
        a (int): Filtro de status ativo (0=todos, 1=ativos, 2=inativos)

    Returns:
        Template renderizado com a lista paginada de funções técnicas
    """
    MAX_PER_PAGE = int(current_app.config.get('MAX_PER_PAGE', 500))

    page = request.args.get('page', default=1, type=int)
    pp = request.args.get('pp', default=50, type=int)
    q = request.args.get('q', default=None, type=str)
    a = request.args.get('a', default=0, type=int)

    if pp > MAX_PER_PAGE:
        pp = MAX_PER_PAGE

    sentenca = db.select(FuncaoTecnica)

    # Filtrar por parte do nome
    if q is not None:
        sentenca = sentenca.filter(FuncaoTecnica.nome.ilike(f"%{q}%"))

    # Filtrar por ativos/inativos
    match a:
        case 1:
            sentenca = sentenca.filter_by(ativo=True)
        case 2:
            sentenca = sentenca.filter_by(ativo=False)
        case _:
            pass

    sentenca = sentenca.order_by(FuncaoTecnica.nome)

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

    return render_template('funcao_tecnica/web/lista.jinja2',
                           title="Lista de funções técnicas",
                           rset_page=rset_page,
                           page=page,
                           q=q,
                           pp=pp,
                           a=a)


@funcao_tecnica_bp.route('/<uuid:funcao_tecnica_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_funcao_tecnica(funcao_tecnica_id: uuid.UUID):
    """Edita uma função técnica existente.

    Args:
        funcao_tecnica_id: UUID da função técnica a ser editada

    Returns:
        Template renderizado com o formulário de edição ou redirect após salvar
    """
    funcao_tecnica: FuncaoTecnica = FuncaoTecnica.get_by_id(funcao_tecnica_id)
    if funcao_tecnica is None:
        flash("Função técnica não encontrada.", category='warning')
        return redirect(url_for('funcoes_tecnicas.listar_funcoes_tecnicas'))

    # Conta o número de pessoas executando esta função
    numero_de_pessoas = len(funcao_tecnica.pessoas)

    form = FuncaoTecnicaEditForm()
    if request.method == 'GET':
        # Preenche o formulário com os dados atuais da função técnica
        form.nome.data = funcao_tecnica.nome
        form.descricao.data = funcao_tecnica.descricao
        form.ativo.data = funcao_tecnica.ativo

    if form.validate_on_submit():
        # Atualiza os campos da função técnica usando os dados do formulário WTForms
        funcao_tecnica.nome = form.nome.data.strip()
        funcao_tecnica.ativo = form.ativo.data

        # Salva as alterações no banco de dados
        try:
            db.session.commit()
            flash("Função técnica atualizada com sucesso.", category='success')
            return redirect(url_for('funcao_tecnica.listar_funcoes_tecnicas'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar função técnica: {e}")
            flash("Ocorreu um erro ao atualizar a função técnica. Tente novamente.", category='danger')

    return render_template('funcao_tecnica/web/editar.jinja2',
                           title="Editar função técnica",
                           form=form,
                           numero_de_pessoas=numero_de_pessoas)
