from flask_wtf import FlaskForm
from wtforms.fields.simple import BooleanField, SubmitField, TextAreaField
from wtforms.fields.choices import SelectField
from wtforms.validators import InputRequired, Length, NumberRange


class AvaliacaoForm(FlaskForm):
    """Formulário para avaliação de filmes.

    Permite que usuários avaliem filmes com nota de 1 a 10,
    comentário opcional e indicação de recomendação.
    """

    nota = SelectField(
            label="Nota",
            choices=[(i, str(i)) for i in range(0, 11)],
            coerce=int,
            default=0,
            validators=[InputRequired(message="É obrigatório informar uma nota"),
                        NumberRange(min=0, max=10, message="A nota deve estar entre 0 e 10"),
                        ]
    )

    comentario = TextAreaField(
            label="Comentário",
            validators=[Length(max=4096, message="O comentário pode ter até 4096 caracteres"),
                        ],
            render_kw={
                'placeholder': 'Compartilhe sua opinião sobre o filme (opcional)',
                'rows'       : 4
            }
    )

    recomendaria = BooleanField(
            label="Recomendaria este filme?",
            default=False
    )

    submit = SubmitField("Salvar Avaliação")
