class EmailValidationService:
    """Serviço responsável pela validação de um endereco de email.
    """

    @staticmethod
    def is_valid(email: str) -> bool:
        """Valida o formato do endereço de email.

        Args:
            email (str): Endereço de email a ser validado.

        Returns:
            bool: True se o formato do email for válido, False caso contrário.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado is not None
        except (EmailNotValidError, EmailSyntaxError, TypeError):
            return False

    @staticmethod
    def normalize(email: str) -> str:
        """Normaliza o endereço de email.

        Args:
            email (str): Endereço de email a ser normalizado.

        Returns:
            str: Endereço de email normalizado.

        Raises:
            ValueError: Se o email for inválido.
        """
        from email_validator import validate_email
        from email_validator.exceptions import EmailNotValidError, EmailSyntaxError
        try:
            validado = validate_email(email, check_deliverability=False)
            return validado.normalized.lower()
        except (EmailNotValidError, EmailSyntaxError, TypeError) as e:
            raise ValueError("Endereço de email inválido.") from e
