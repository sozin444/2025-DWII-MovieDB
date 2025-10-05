from flask import Blueprint, flash, redirect, render_template, url_for

from app.forms.auth import RegistrationForm
from app.services.user_service import UserService, UserOperationStatus

auth_bp = Blueprint(name='auth',
                    import_name=__name__,
                    url_prefix='/auth',
                    template_folder="templates", )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Exibe o formulário de registro de usuário e processa o cadastro.

    Usuários já autenticados não podem acessar esta rota. Se o formulário for
    enviado e validado, delega o registro ao UserService. Caso contrário,
    renderiza o template de registro.

    Returns:
        flask.Response: Redireciona para a página inicial ou renderiza o template
            de registro.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        resultado = UserService.registrar_usuario(
                nome=form.nome.data,
                email=form.email.data,
                password=form.password.data,
        )

        if resultado.status == UserOperationStatus.SUCCESS:
            flash("Cadastro efetuado com sucesso.", category='success')
            return redirect(url_for('root.index'))
        else:
            flash(f"Erro ao registrar usuário: {resultado.error_message}", category='danger')

    return render_template('auth/web/register.jinja2',
                           title="Cadastrar um novo usuário",
                           form=form)
