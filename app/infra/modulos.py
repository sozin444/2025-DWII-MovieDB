from flask_bootstrap import Bootstrap5
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

bootstrap = Bootstrap5()
db = SQLAlchemy()
migrate = Migrate()
