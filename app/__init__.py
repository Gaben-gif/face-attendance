import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'face_attendance.sqlite3')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(app.instance_path, "images"),
    )

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403     

    db.init_app(app)
    login.init_app(app)

    from . import routes, models
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app