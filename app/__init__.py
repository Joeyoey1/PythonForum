from flask import Flask, send_from_directory
from flask_login import LoginManager
from .models import db, User, Role, Entry, FTSEntry, Reply, UserFollow
from .config import Config
import os

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
    app.config.from_object(config_class)

    # Initialize DB
    db_path = app.config['DATABASE'].replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, '..', db_path)
    db.init(db_path)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_name):
        return User.get_or_none(User.user_name == user_name)

    from .blueprints.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .blueprints.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(_exc):
        if not db.is_closed():
            db.close()

    with app.app_context():
        db.connect(reuse_if_open=True)
        db.create_tables([User, Role, Entry, FTSEntry, Reply, UserFollow])
        Role.get_or_create(name='User')
        Role.get_or_create(name='Moderator')
        Role.get_or_create(name='Admin')

    return app
