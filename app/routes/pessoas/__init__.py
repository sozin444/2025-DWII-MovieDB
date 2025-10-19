from flask import Blueprint

from app.models import Pessoa
from app.services.imageprocessing_service import ImageProcessingService

pessoa_bp = Blueprint(name='pessoa',
                      import_name=__name__,
                      url_prefix='/pessoa',
                      template_folder="templates", )


@pessoa_bp.route('/<uuid:pessoa_id>/foto', methods=['GET'])
def pessoa_foto(pessoa_id):
    """Serve a foto da pessoa

    Args:
        pessoa_id (uuid.UUID): ID da pessoa.

    Returns:
        flask.Response: Imagem da foto da pessoa.
    """
    pessoa = Pessoa.get_by_id(pessoa_id)

    if pessoa:
        foto_data, mime_type = pessoa.foto
        return ImageProcessingService.servir_imagem(foto_data, mime_type)
    else:
        # Usuário não encontrado - retorna placeholder
        placeholder_data = ImageProcessingService.gerar_placeholder(300, 400,
                                                                    "Pessoa\nnão encontrada",
                                                                    36)
        return ImageProcessingService.servir_imagem(placeholder_data, 'image/png')
