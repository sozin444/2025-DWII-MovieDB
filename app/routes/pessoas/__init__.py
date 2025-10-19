from flask import abort, Blueprint, render_template

from app.models import Pessoa
from app.services.imageprocessing_service import ImageProcessingService
from app.services.pessoa_service import PessoaService
from app.services.ator_service import AtorService

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


@pessoa_bp.route('/<uuid:pessoa_id>/detail', methods=['GET'])
def pessoa_detalhes(pessoa_id):
    """Apresenta os detalhes completos de uma pessoa.
    
    Args:
        pessoa_id (uuid.UUID): ID da pessoa
        
    Returns:
        Template renderizado com detalhes da pessoa
        
    Raises:
        404: Se a pessoa não for encontrada
    """
    pessoa = Pessoa.get_by_id(pessoa_id)
    
    if not pessoa:
        abort(404)
    
    # Obter funções técnicas da pessoa
    funcoes_tecnicas = PessoaService.obter_funcoes(pessoa)
    
    # Obter papéis de atuação se a pessoa for ator
    papeis = []
    if pessoa.ator:
        papeis = AtorService.obter_papeis(pessoa.ator)
    
    return render_template('pessoa/web/details.jinja2',
                           title=f"Detalhes de '{pessoa.nome}'",
                           pessoa=pessoa,
                           papeis=papeis,
                           funcoes_tecnicas=funcoes_tecnicas)
