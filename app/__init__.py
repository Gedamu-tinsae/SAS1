from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('instance.config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
