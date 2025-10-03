import json
import logging
import os
import sys

from flask import Flask

from app.infra import app_logging


def create_app(config_filename: str = 'config.dev.json') -> Flask:
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates',
                )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app_logging.configure_logging(logging.DEBUG)

    app.logger.debug("Lendo a configuração da aplicação a partir do arquivo '%s'" % (config_filename,))
    try:
        app.config.from_file(config_filename,load=json.load)
    except FileNotFoundError:
        app.logger.fatal("O arquivo de configuração '%s' não existe" % (config_filename,))
        sys.exit(1)
    except json.JSONDecodeError as e:
        app.logger.fatal("O arquivo de configuração '%s' não é um JSON válido: %s" % (config_filename, str(e),))
        sys.exit(1)
    except Exception as e:
        app.logger.fatal("Erro ao carregar o arquivo de configuração '%s': %s" % (config_filename, str(e),))
        sys.exit(1)

    if "APP_HOST" not in app.config or \
            not isinstance(app.config.get("APP_HOST"), str) or \
            app.config.get("APP_HOST") == "":
        app.logger.warning("A chave 'APP_HOST' não está presente no "
                           "arquivo de configuração. Utilizando 0.0.0.0")
        app.config["APP_HOST"] = "0.0.0.0"

    if "APP_PORT" not in app.config or \
            not isinstance(app.config.get("APP_PORT"), int) or \
            not (0 < app.config.get("APP_PORT") < 65536):
        app.logger.warning("A chave 'APP_PORT' não está presente no "
                           "arquivo de configuração. Utilizando 5000")
        app.config["APP_PORT"] = 5000

    app.logger.debug("Registrando blueprints")
    from .routes.root import root_bp
    app.register_blueprint(root_bp)

    app.logger.info("Aplicação configurada com sucesso")
    return app
