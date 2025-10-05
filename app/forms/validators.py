import re
from collections import namedtuple

from flask import current_app
from wtforms import ValidationError

from app.models.autenticacao import User
from app.services.email_service import EmailValidationService


class UniqueEmail(object):
    """
    Validador WTForms para garantir que o email informado não está cadastrado no sistema.

    Args:
        message (Optional[str]): Mensagem de erro personalizada.
    """

    def __init__(self, message=None):
        if not message:
            message = "Já existe um usuário com este email"
        self.message = message

    def __call__(self, form, field):
        """
        Verifica se um email já está cadastrado.

        Args:
            form: O formulário sendo validado.
            field: O campo de email a ser verificado.

        Raises:
            ValidationError: Se o email já estiver cadastrado.
        """
        try:
            email = EmailValidationService.normalize(field.data)
        except ValueError:
            raise ValidationError("Endereço de email inválido.")
        if User.get_by_email(email):
            raise ValidationError(self.message)


class SenhaComplexa(object):
    """
    Validador WTForms para garantir que a senha informada atende aos requisitos de complexidade definidos.

    Os requisitos são definidos pelas seguintes chaves inteiras e booleanas no dicionário de
    configuração da aplicação:

    - PASSWORD_MIN: 8
    - PASSWORD_MINUSCULA: false
    - PASSWORD_NUMERO: false
    - PASSWORD_SIMBOLO: false
    - PASSWORD_MAIUSCULA: false
    """

    def __init__(self):
        pass

    def __call__(self, form, field):
        """
        Realiza a validação da senha conforme os requisitos definidos.

        Args:
            form: O formulário sendo validado.
            field: O campo de senha a ser verificado.

        Raises:
            ValidationError: Se a senha não atender aos requisitos de complexidade.
        """
        Teste = namedtuple('Teste', ['config', 'mensagem', 're'])

        lista_de_testes = [
            Teste('PASSWORD_MAIUSCULA', "letras maiúsculas", r'[A-Z]'),
            Teste('PASSWORD_MINUSCULA', "letras minúsculas", r'[a-z]'),
            Teste('PASSWORD_NUMERO', "números", r'\d'),
            Teste('PASSWORD_SIMBOLO', "símbolos especiais", r'\W')
        ]

        min_caracteres = current_app.config.get('PASSWORD_MIN', 0)
        senha_valida = (len(field.data) >= min_caracteres)
        mensagens = [f"pelo menos {min_caracteres} caracteres"]

        for teste in lista_de_testes:
            if current_app.config.get(teste.config, False):
                senha_valida = senha_valida and (re.search(teste.re, field.data) is not None)
                mensagens.append(teste.mensagem)

        mensagem = "A sua senha precisa conter "
        if len(mensagens) > 1:
            mensagem = mensagem + " e ".join([", ".join(mensagens[:-1]), mensagens[-1]])
        else:
            mensagem = mensagem + mensagens[0]
        mensagem = mensagem + "."

        if not senha_valida:
            raise ValidationError(mensagem)

        return
