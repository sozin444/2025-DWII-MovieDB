from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import anonymous_required
from app.forms.auth import AskToResetPasswordForm, LoginForm, RegistrationForm, SetNewPasswordForm
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

            # Verifica a idade da senha
            max_age = current_app.config.get('PASSWORD_MAX_AGE', 0)
            if max_age > 0:
                idade_senha = UserService.verificar_idade_senha(usuario)
                if idade_senha is not None and idade_senha > max_age:
                    flash(f"Sua senha tem {idade_senha} dias. Por motivos de segurança, "
                          f"recomendamos que você altere sua senha.",
                          category='warning')

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


@auth_bp.route('/new_password', methods=['GET', 'POST'])
@anonymous_required
def new_password():
    """Exibe o formulário para solicitar redefinição de senha.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a geração de token e envio de email. Sempre exibe uma mensagem informando
    que, se houver uma conta, um email será enviado. Renderiza o formulário caso
    não seja enviado ou validado.

    Returns:
        flask.Response: Redireciona para a página de login ou renderiza o formulário.
    """
    email_service = current_app.extensions.get('email_service')
    if not email_service:
        raise ValueError("EmailService não configurado na aplicação")

    form = AskToResetPasswordForm()
    if form.validate_on_submit():
        email = form.email.data

        # Solicita reset (o serviço normaliza o email internamente)
        resultado = UserService.solicitar_reset_senha(email, email_service)

        # Por segurança, sempre exibe a mesma mensagem
        flash(f"Se houver uma conta com o email {email}, uma mensagem será enviada com as "
              f"instruções para a troca da senha", category='info')

        # Opcionalmente, exibe erro de envio
        if resultado.status == UserOperationStatus.SEND_EMAIL_ERROR:
            flash("Erro no envio do email de redefinição de senha", category="danger")

        return redirect(url_for('auth.login'))

    return render_template('auth/web/ask_for_email.jinja2',
                           title="Solicitar nova senha",
                           title_card="Redefinir minha senha",
                           form=form)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
@anonymous_required
def reset_password(token):
    """Exibe o formulário para redefinição de senha e processa a troca de senha.

    Usuários autenticados não podem acessar esta rota. Delega ao UserService
    a validação do token e redefinição da senha. Em caso de token inválido ou
    usuário inexistente, exibe mensagem de erro.

    Args:
        token (str): Token JWT enviado na URL para redefinição de senha.

    Returns:
        flask.Response: Redireciona para a página de login ou inicial, ou renderiza
            o formulário de redefinição de senha.
    """
    form = SetNewPasswordForm()
    if form.validate_on_submit():
        resultado = UserService.redefinir_senha_por_token(token, form.password.data)

        if resultado.status == UserOperationStatus.SUCCESS:
            flash("Sua senha foi redefinida com sucesso", category='success')
            return redirect(url_for('auth.login'))
        elif resultado.status == UserOperationStatus.TOKEN_EXPIRED:
            flash("O token expirou. Solicite uma nova redefinição de senha", category='warning')
            return redirect(url_for('auth.new_password'))
        elif resultado.status == UserOperationStatus.INVALID_TOKEN:
            flash("Token inválido ou expirado", category='warning')
            return redirect(url_for('root.index'))
        else:
            flash("Erro ao redefinir senha", category='warning')
            return redirect(url_for('root.index'))

    return render_template('auth/web/new_password.jinja2',
                           title="Redefinir senha",
                           title_card="Escolha uma nova senha",
                           form=form)
