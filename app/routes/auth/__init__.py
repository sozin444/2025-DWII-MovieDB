from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import anonymous_required
from app.forms.auth import LoginForm, RegistrationForm
from app.models import User
from app.services.user_service import UserOperationStatus, UserService

auth_bp = Blueprint(name='auth',
                    import_name=__name__,
                    url_prefix='/auth',
                    template_folder="templates", )


@auth_bp.route('/register', methods=['GET', 'POST'])
@anonymous_required
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
            flash("Cadastro efetuado com sucesso. Antes de logar na aplicação, ative a "
                  "sua conta seguindo as instruções da mensagem de email que lhe foi "
                  "enviada.", category='success')
            return redirect(url_for('root.index'))
        else:
            flash(f"Erro ao registrar usuário: {resultado.error_message}", category='danger')

    return render_template('auth/web/register.jinja2',
                           title="Cadastrar um novo usuário",
                           form=form)


@auth_bp.route('/ativar_usuario/<token>')
@anonymous_required
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
        return redirect(url_for('auth.login'))
    elif resultado.status == UserOperationStatus.USER_ALREADY_ACTIVE:
        flash(f"Conta já havia sido ativada e o email {resultado.user.email} validado.",
              category='info')
        return redirect(url_for('auth.login'))
    else:
        flash("Processo de ativação da conta falhou. Inicie uma nova ativação.", category='warning')
    return redirect(url_for('root.index'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """Exibe o formulário de login e processa a autenticação do usuário.

    Usuários já autenticados não podem acessar esta rota. Se o formulário for
    enviado e validado, verifica as credenciais do usuário. Se o usuário existir,
    estiver ativo e a senha estiver correta, realiza o login. Se efetuar o login
    redireciona para a página desejada ou para a página inicial. Caso contrário,
    exibe mensagens de erro e permanece na página de login.

    Returns:
        flask.Response: Redireciona para a página desejada, página inicial ou
            renderiza o template de login.
    """
    form = LoginForm()

    if form.validate_on_submit():
        from app.services.email_service import EmailValidationService

        try:
            email_normalizado = EmailValidationService.normalize(form.email.data)
        except ValueError:
            flash("Email ou senha incorretos", category='warning')
            return render_template('auth/web/login.jinja2',
                                   title="Login",
                                   form=form)

        usuario = User.get_by_email(email_normalizado)

        if usuario is None or not usuario.check_password(form.password.data):
            flash("Email ou senha incorretos", category='warning')
        elif not UserService.pode_logar(usuario):
            flash("Sua conta ainda não foi ativada. Verifique seu email.", category='warning')
        else:
            UserService.efetuar_login(usuario, remember_me=form.remember_me.data)
            flash(f"Usuario {usuario.email} logado", category='success')

            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('root.index')
            return redirect(next_page)

    return render_template('auth/web/login.jinja2',
                           title="Login",
                           form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Realiza o logout do usuário autenticado.

    Encerra a sessão do usuário, exibe uma mensagem de sucesso e redireciona
    para a página inicial.

    Returns:
        flask.Response: Redireciona para a página inicial após logout.
    """
    UserService.efetuar_logout(current_user)
    flash("Logout efetuado com sucesso!", category='success')
    return redirect(url_for('root.index'))
