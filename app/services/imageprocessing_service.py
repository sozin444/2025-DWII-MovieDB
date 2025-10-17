import hashlib
import io
import re
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Optional, Tuple

from flask import current_app, Response
from PIL import Image, ImageDraw, ImageFont


class ImageProcessingError(Exception):
    """Exceção customizada para erros de processamento de imagem.
    """
    pass


@dataclass
class ImageProcessingResult:
    imagem_base64: str  # Imagem original em base64
    avatar_base64: str  # Avatar redimensionado em base64
    mime_type: str  # Tipo MIME da imagem
    formato_original: str  # Formato original (JPEG, PNG, etc)
    dimensoes_originais: Tuple[int, int]  # (largura, altura) original
    dimensoes_avatar: Tuple[int, int]  # (largura, altura) do avatar
    tamanho_arquivo: int  # Tamanho do arquivo original em bytes


class ImageProcessingService:
    """Serviço responsável por processamento e manipulação de imagens.
    """
    # Formatos suportados
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP'}

    # Extensões permitidas (para validação de upload)
    ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp']

    # Tamanhos padrão
    DEFAULT_AVATAR_SIZE = 64
    DEFAULT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    DEFAULT_MAX_DIMENSIONS = (2048, 2048)

    # Qualidade de compressão
    JPEG_QUALITY = 85
    PNG_OPTIMIZE = True

    @staticmethod
    def processar_upload_foto(arquivo_upload,
                              avatar_size: Optional[int] = None,
                              max_file_size: Optional[int] = None,
                              max_dimensions: Optional[
                                  Tuple[int, int]] = None) -> ImageProcessingResult:
        """Processa um arquivo de imagem enviado via upload, gerando foto original e avatar.

        Args:
            arquivo_upload (FileStorage): Objeto de arquivo (FileStorage do Flask).
            avatar_size (Optional[int]): Tamanho do avatar em pixels. Se None, usa configuração da app ou 32.
            max_file_size (Optional[int]): Tamanho máximo do arquivo em bytes. Se None, usa configuração da app ou 5MiB.
            max_dimensions (Optional[Tuple[int, int]]): Dimensões máximas permitidas (largura, altura). Se None, usa configuração da app ou (2048, 2048).

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem.

        Raises:
            ImageProcessingError: Em caso de erro no processamento.
            ValueError: Para arquivos inválidos ou muito grandes.
        """
        if arquivo_upload is None:
            raise ValueError("Nenhum arquivo fornecido")

        # Configurações com fallbacks
        avatar_size = avatar_size or current_app.config.get('AVATAR_SIZE',
                                                            ImageProcessingService.DEFAULT_AVATAR_SIZE)
        max_file_size = max_file_size or current_app.config.get('MAX_IMAGE_SIZE',
                                                                ImageProcessingService.DEFAULT_MAX_FILE_SIZE)
        max_dimensions = max_dimensions or current_app.config.get('MAX_IMAGE_DIMENSIONS',
                                                                  ImageProcessingService.DEFAULT_MAX_DIMENSIONS)

        try:
            # Lê os dados do arquivo
            arquivo_upload.seek(0)  # Garante que está no início
            imagem_data = arquivo_upload.read()

            if not imagem_data:
                raise ValueError("Arquivo de imagem vazio")

            # Validação de tamanho
            if len(imagem_data) > max_file_size:
                raise ValueError(
                        f"Arquivo muito grande. Máximo permitido: "
                        f"{max_file_size / (1024 * 1024):.1f}MB")

            # Processa a imagem
            return ImageProcessingService._processar_imagem_bytes(imagem_data,
                                                                  arquivo_upload.mimetype,
                                                                  avatar_size, max_dimensions)

        except (AttributeError, OSError) as e:
            raise ImageProcessingError(f"Erro ao processar arquivo de imagem: {str(e)}") from e

    @staticmethod
    def processar_base64(base64_string: str,
                         avatar_size: Optional[int] = None,
                         max_file_size: Optional[int] = None,
                         max_dimensions: Optional[Tuple[int, int]] = None) -> ImageProcessingResult:
        """Processa uma imagem em formato base64 (data URI ou base64 puro).

        Args:
            base64_string (str): String base64 da imagem (pode incluir data URI prefix).
            avatar_size (Optional[int]): Tamanho do avatar em pixels.
            max_file_size (Optional[int]): Tamanho máximo do arquivo em bytes.
            max_dimensions (Optional[Tuple[int, int]]): Dimensões máximas permitidas.

        Returns:
            ImageProcessingResult: Resultado do processamento da imagem.

        Raises:
            ImageProcessingError: Em caso de erro no processamento.
            ValueError: Para dados inválidos.
        """
        if not base64_string:
            raise ValueError("String base64 vazia")

        # Configurações com fallbacks
        avatar_size = avatar_size or current_app.config.get('AVATAR_SIZE',
                                                            ImageProcessingService.DEFAULT_AVATAR_SIZE)
        max_file_size = max_file_size or current_app.config.get('MAX_IMAGE_SIZE',
                                                                ImageProcessingService.DEFAULT_MAX_FILE_SIZE)
        max_dimensions = max_dimensions or current_app.config.get('MAX_IMAGE_DIMENSIONS',
                                                                  ImageProcessingService.DEFAULT_MAX_DIMENSIONS)

        try:
            # Remove o prefixo data URI se presente (ex: "data:image/jpeg;base64,")
            mime_type = 'image/jpeg'  # default
            if base64_string.startswith('data:'):
                match = re.match(r'data:(image/[a-z]+);base64,(.+)', base64_string)
                if match:
                    mime_type = match.group(1)
                    base64_string = match.group(2)
                else:
                    raise ValueError("Formato de data URI inválido")

            # Decodifica base64
            imagem_data = b64decode(base64_string)

            if not imagem_data:
                raise ValueError("Dados de imagem vazios após decodificação")

            # Validação de tamanho
            if len(imagem_data) > max_file_size:
                raise ValueError(
                        f"Arquivo muito grande. Máximo permitido: "
                        f"{max_file_size / (1024 * 1024):.1f}MB")

            # Processa a imagem
            return ImageProcessingService._processar_imagem_bytes(imagem_data, mime_type,
                                                                  avatar_size, max_dimensions)

        except (ValueError, TypeError) as e:
            if isinstance(e, ValueError):
                raise
            raise ImageProcessingError(f"Erro ao decodificar base64: {str(e)}") from e

    @staticmethod
    def _processar_imagem_bytes(imagem_data: bytes,
                                mime_type: str,
                                avatar_size: int,
                                max_dimensions: Tuple[int, int]) -> ImageProcessingResult:
        """Processa dados de imagem em bytes.

        Args:
            imagem_data (bytes): Dados da imagem em bytes.
            mime_type (str): Tipo MIME fornecido pelo upload.
            avatar_size (int): Tamanho do avatar.
            max_dimensions (Tuple[int, int]): Dimensões máximas.

        Returns:
            ImageProcessingResult: Resultado do processamento.
        """
        try:
            with Image.open(io.BytesIO(imagem_data)) as imagem:
                # Validações básicas
                if not hasattr(imagem, 'format') or imagem.format is None:
                    raise ImageProcessingError("Formato de imagem não reconhecido")

                if imagem.format not in ImageProcessingService.SUPPORTED_FORMATS:
                    raise ImageProcessingError(f"Formato {imagem.format} não suportado. "
                                               f"Formatos aceitos: "
                                               f"{', '.join(ImageProcessingService.SUPPORTED_FORMATS)}")

                largura_orig, altura_orig = imagem.size

                # Validação de dimensões
                if largura_orig > max_dimensions[0] or altura_orig > max_dimensions[1]:
                    raise ValueError(
                            f"Imagem muito grande. Máximo: {max_dimensions[0]}x{max_dimensions[
                                1]} pixels")

                # Salva foto original em buffer
                buffer_imagem = io.BytesIO()
                imagem.save(buffer_imagem, format=imagem.format, optimize=True)
                foto_bytes = buffer_imagem.getvalue()

                # Gera avatar
                avatar_data, avatar_dims = ImageProcessingService._gerar_avatar(imagem, avatar_size)

                return ImageProcessingResult(
                        imagem_base64=b64encode(foto_bytes).decode('utf-8'),
                        avatar_base64=b64encode(avatar_data).decode('utf-8'),
                        mime_type=mime_type,
                        formato_original=imagem.format,
                        dimensoes_originais=(largura_orig, altura_orig),
                        dimensoes_avatar=avatar_dims,
                        tamanho_arquivo=len(imagem_data))

        except Exception as e:
            if isinstance(e, (ImageProcessingError, ValueError)):
                raise
            raise ImageProcessingError(f"Erro no processamento da imagem: {str(e)}") from e

    @staticmethod
    def _gerar_avatar(imagem: Image.Image,
                      avatar_size: int) -> Tuple[bytes, Tuple[int, int]]:
        """Gera avatar redimensionado a partir da imagem.

        Redimensiona a imagem proporcionalmente mantendo o aspect ratio original,
        de forma que nenhuma dimensão exceda avatar_size. Se a imagem já for menor
        que o tamanho desejado, não há redimensionamento (evita upscaling).

        Args:
            imagem (PIL.Image.Image): Objeto PIL Image.
            avatar_size (int): Tamanho máximo desejado do avatar (largura ou altura).

        Returns:
            typing.Tuple[bytes, typing.Tuple[int, int]]: Tupla contendo (dados_avatar, dimensoes_finais).

        Note:
            Utiliza Image.Resampling.LANCZOS para alta qualidade no redimensionamento.
        """
        largura, altura = imagem.size
        formato_original = imagem.format

        imagem_avatar = imagem.copy()
        # Otimização: pula redimensionamento se já está no tamanho adequado
        if max(largura, altura) > avatar_size:
            # Calcula novo tamanho mantendo proporção
            fator_escala = min(avatar_size / largura, avatar_size / altura)
            novo_tamanho = (
                int(largura * fator_escala),
                int(altura * fator_escala)
            )
            imagem_avatar = imagem.copy()
            imagem_avatar.thumbnail(novo_tamanho, Image.Resampling.LANCZOS)
        buffer_avatar = io.BytesIO()
        imagem_avatar.save(buffer_avatar, format=formato_original, optimize=True)
        return buffer_avatar.getvalue(), imagem_avatar.size

    @staticmethod
    def generate_identicon_base64(data: str,
                                  grid_size: int = 8,
                                  image_size: int = 128,
                                  foreground: Optional[list] = None,
                                  background: Optional[str] = None) -> tuple[str, str]:
        """Gera um identicon em PNG com fundo transparente, codificado em base64, a partir de uma string.

        Args:
            data (str): String usada para gerar o identicon (ex: e-mail ou nome de usuário).
            grid_size (int, opcional): Número de blocos na grade (ex: 8 para 8x8). Padrão: 9. Máximo: 15.
            image_size (int, opcional): Tamanho da imagem em pixels (ex: 240 para 240x240). Padrão: 128. Máximo: 256.
            foreground (list, opcional): Lista de cores hexadecimais para o identicon. Padrão: uma paleta de cores.
            background (str, opcional): Cor de fundo em hexadecimal. Padrão: None (transparente).

        Returns:
            str: String base64 contendo o PNG do identicon.
            str: Tipo MIME da imagem ("image/png").

        Raises:
            ImageProcessingError: Em caso de erro na geração do identicon.
        """
        import pydenticon
        import re

        grid_size = max(1, min(grid_size, 15))
        image_size = max(16, min(image_size, 256))

        # Valores padrão se não forem fornecidos
        if foreground is None:
            foreground = [
                "#1abc9c", "#16a085", "#2ecc71", "#27ae60", "#3498db",
                "#2980b9", "#9b59b6", "#8e44ad", "#e67e22", "#d35400",
                "#e74c3c", "#c0392b", "#f1c40f", "#f39c12", "#34495e"
            ]

        if background is not None:
            if not isinstance(background, str) or not re.match(r'^#([A-Fa-f0-9]{6})$', background):
                background = None  # Reseta para None se inválido

        try:
            generator = pydenticon.Generator(
                    grid_size, grid_size,
                    digest=hashlib.sha512,
                    foreground=foreground,
                    background=background
            )
            identicon_png = generator.generate(data, image_size, image_size, output_format="png")
        except ValueError:
            raise ImageProcessingError("Erro ao gerar identicon com os parâmetros fornecidos.")
        except Exception as e:
            raise ImageProcessingError(f"Erro inesperado ao gerar identicon: {str(e)}") from e
        identicon_base64 = b64encode(identicon_png).decode("utf-8")

        return identicon_base64, "image/png"

    @staticmethod
    def gerar_placeholder(largura: int,
                          altura: int,
                          texto: Optional[str] = None,
                          tamanho_fonte: Optional[int] = None) -> bytes:
        """Gera uma imagem placeholder com texto centralizado.

        Args:
            largura (int): Largura da imagem em pixels
            altura (int): Altura da imagem em pixels
            texto (str, opcional): Texto a ser exibido (pode conter \n)
            tamanho_fonte (int, opcional): Tamanho da fonte

        Returns:
            bytes: Dados da imagem PNG em bytes

        Raises:
            ImageProcessingError: Se texto for fornecido mas tamanho_fonte não for.
        """
        if texto and not tamanho_fonte:
            raise ImageProcessingError(
                "Se texto for fornecido, tamanho_fonte deve ser especificado.")

        img = Image.new('RGB', (largura, altura), color='#6c757d')
        draw = ImageDraw.Draw(img)

        if texto and tamanho_fonte:
            try:
                fonte = ImageFont.truetype("arial.ttf", tamanho_fonte)
            except (OSError, ValueError):
                fonte = ImageFont.load_default(size=tamanho_fonte)
            except Exception as e:
                raise ImageProcessingError(f"Erro ao carregar fonte: {str(e)}") from e

            bbox = draw.textbbox((0, 0), texto, font=fonte)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((largura - text_width) // 2, (altura - text_height) // 2)
            draw.text(position, texto, fill='white', align='center', font=fonte)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def servir_imagem(imagem_data: bytes,
                      mime_type: str = 'image/png') -> Response:
        """Cria uma Response com headers apropriados para servir imagem.

        Args:
            imagem_data (bytes): Dados da imagem
            mime_type (str): Tipo MIME da imagem. Default: 'image/png'

        Returns:
            Response: Response Flask com headers de cache
        """
        response = Response(imagem_data, mimetype=mime_type)
        response.headers['Content-Type'] = mime_type
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
