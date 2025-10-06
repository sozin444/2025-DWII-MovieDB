from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app.forms.auth import RegistrationForm
from app.services.user_service import UserOperationStatus, UserService

auth_bp = Blueprint(name='auth',
                    import_name=__name__,
                    url_prefix='/auth',
                    template_folder="templates", )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Exibe o formulário de registro de usuário e processa o cadastro.

    Usuários já autenticados não podem acessar esta rota. Se o formulário for
    enviado e validado, delega o registro ao UserService. O usuário deve confirmar
    o email antes de conseguir logar. Caso contrário, renderiza o template de registro.

    Returns:
        flask.Response: Redireciona para a página inicial ou renderiza o template
            de registro.
    """
    email_service = current_app.extensions.get('email_service')
    if not email_service:
        raise ValueError("EmailService não configurado na aplicação")

    form = RegistrationForm()
    if form.validate_on_submit():
        resultado = UserService.registrar_usuario(
                nome=form.nome.data,
                email=form.email.data,
                password=form.password.data,
                email_service=email_service
        )

        if resultado.status == UserOperationStatus.SUCCESS:
            flash("Cadastro efetuado com sucesso.", category='success')
            return redirect(url_for('root.index'))
        else:
            flash(f"Erro ao registrar usuário: {resultado.error_message}", category='danger')

    return render_template('auth/web/register.jinja2',
                           title="Cadastrar um novo usuário",
                           form=form)


@auth_bp.route('/ativar_usuario/<token>')
def ativar_usuario(token):
    """Valida o email do usuário a partir de um token JWT enviado na URL.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a validação do token e ativação do usuário. Exibe mensagens de sucesso ou
    erro conforme o caso.

    Args:
        token (str): Token JWT enviado na URL para validação do email.

    Returns:
        flask.Response: Redireciona para a página de login ou inicial, conforme o caso.
    """
    resultado = UserService.ativar_usuario_por_token(token)

    if resultado.status == UserOperationStatus.SUCCESS:
        flash(f"Conta ativada e email {resultado.user.email} validado!", category='success')
    elif resultado.status == UserOperationStatus.USER_ALREADY_ACTIVE:
        flash(f"Conta já havia sido ativada e o email {resultado.user.email} validado.",
              category='info')
    else:
        flash("Processo de ativação da conta falhou. Inicie uma nova ativação.", category='warning')
    return redirect(url_for('root.index'))
