from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms.fields.simple import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from ..validators import CampoImutavel, SenhaComplexa, UniqueEmail


class RegistrationForm(FlaskForm):
    """Formulário para cadastro de usuário com validação de email.

    Valida o nome do usuário, a exclusividade do email e a complexidade da senha.
    """
    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome para cadastro"),
                        Length(max=60, message="O nome pode ter até 60 caracteres")])
    email = StringField(
            label="Email",
            validators=[InputRequired(message="É obrigatório informar um email para cadastro"),
                        Email(message="Informe um email válido"),
                        Length(max=180, message="O email pode ter até 180 caracteres"),
                        UniqueEmail(message="Este email já está cadastrado no sistema")])
    password = PasswordField(
            label="Senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a senha",
            validators=[InputRequired(message="É necessário repetir a senha"),
                        EqualTo('password', message="As senhas não são iguais")])
    submit = SubmitField("Criar uma conta no sistema")


class LoginForm(FlaskForm):
    """
    Form for user login with email and password.

    Includes optional remember me functionality.
    """
    email = StringField(
                label="Email",
                validators=[InputRequired(message="É obrigatório informar um email para login"),
                            Email(message="Informe um email válido"),
                            Length(max=180, message="O email pode ter até 180 caracteres")])
    password = PasswordField(
                label="Senha",
                validators=[InputRequired(message="É necessário informar a senha")])
    remember_me = BooleanField(
                label="Permanecer conectado?",
                default=True)
    submit = SubmitField("Entrar")


class AskToResetPasswordForm(FlaskForm):
    """Formulário para solicitar redefinição de senha.

    Valida o formato do email antes de enviar o link de redefinição de senha.
    """
    email = StringField(
            label="Email",
            validators=[
                InputRequired(message="É obrigatório informar o email para o qual se deseja "
                                      "definir nova senha"),
                Email(message="Informe um email válido"),
                Length(max=180, message="O email pode ter até 180 caracteres")
            ])
    submit = SubmitField("Solicitar redefinição de senha")


class SetNewPasswordForm(FlaskForm):
    """Formulário para definir nova senha após reset.

    Valida a complexidade da senha e confirma que as senhas correspondem.
    """
    password = PasswordField(
            label="Nova senha",
            validators=[InputRequired(message="É necessário escolher uma senha"),
                        SenhaComplexa()])
    password2 = PasswordField(
            label="Confirme a senha",
            validators=[InputRequired(message="É necessário repetir a senha"),
                        EqualTo('password', message="As senhas não são iguais")])
    submit = SubmitField("Redefinir senha")


class ProfileForm(FlaskForm):
    """
    Form for updating user profile information.

    Allows modification of name, 2FA settings, and profile photo.
    Email is immutable once set.
    """

    def __init__(self, user=None, **kwargs):
        """
        Initialize profile form with reference user.

        Args:
            user: moviedb.models.user.User | None: User object to validate against, defaults to current_user.
            **kwargs: dict: Additional keyword arguments passed to FlaskForm.
        """
        super().__init__(**kwargs)
        self.reference_obj = user or current_user

    id = HiddenField(validators=[CampoImutavel(field_name='id',
                                               message="Você não pode alterar o ID do usuário.")])

    nome = StringField(
            label="Nome",
            validators=[InputRequired(message="É obrigatório informar um nome"),
                        Length(max=60,
                               message="O nome pode ter até 60 caracteres")])
    email = StringField(
            label="Email",
            validators=[CampoImutavel(field_name='email',
                                      message="Você não pode alterar o email.")])

    submit = SubmitField("Efetuar as mudanças")
