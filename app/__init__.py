from pathlib import Path

from flask import Flask

def create_app():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    app = Flask(__name__, template_folder="templates")
    app.secret_key = "dev-secret-change"  # замінити у продакшені
    app.config["UPLOAD_FOLDER"] = str(data_dir)

    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    return app
