from flask import Blueprint, render_template

root_bp = Blueprint('root',
                    __name__,
                    url_prefix='/',
                    template_folder='templates',
                    )


@root_bp.route("/")
def index():
    """
    Retorna a página principal da aplicação.

    Returns:
        str: Página HTML da página principal.
    """
    return render_template("root/index.jinja2",
                           title="Página principal")
