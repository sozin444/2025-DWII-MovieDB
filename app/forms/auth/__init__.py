from flask_wtf import FlaskForm
from wtforms.fields.simple import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, InputRequired, Length

from ..validators import SenhaComplexa, UniqueEmail


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
