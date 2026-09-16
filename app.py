import os

from flask import Flask, Response, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import cors, db, socketio
from routes import register_blueprints
from routes.pages import register_page_routes
from services.seed_service import seed_data

# Importing this module registers Socket.IO event handlers.
import socket_events  # noqa: F401


def configure_upload_folders(app):
    """Create all folders used by user uploads."""
    base = os.path.join(app.root_path, "static", "uploads")
    folders = {
        "UPLOAD_FOLDER": base,
        "AVATAR_UPLOAD_FOLDER": os.path.join(base, "avatars"),
        "NOTE_UPLOAD_FOLDER": os.path.join(base, "notes"),
        "CHAT_UPLOAD_FOLDER": os.path.join(base, "chat"),
        "COMMUNITY_UPLOAD_FOLDER": os.path.join(base, "communities"),
        "MEETING_UPLOAD_FOLDER": os.path.join(base, "meetings"),
    }

    app.config.update(folders)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    configure_upload_folders(app)

    # Respect HTTPS / host headers supplied by a reverse proxy such as Render.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    cors.init_app(app, supports_credentials=True)
    socketio.init_app(app)

    register_blueprints(app)
    register_page_routes(app)



    @app.get("/sw.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    with app.app_context():
        db.create_all()
        seed_data()

    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    print("\nCampus AI 已啟動")
    print(f"本機開啟：http://127.0.0.1:{port}")
    print("部署到雲端後，可由任何網路透過 HTTPS 網址使用。\n")

    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True,
    )
