from .ovs_show import register_show_routes
from .ovs_backup import register_backup_routes
from .ovs_load_config import load_config_bp
from .api_backups import backup_api  # ✅ Import the Blueprint

from flask import send_from_directory

def init_routes(app):
    @app.route('/')
    def serve_index():
        return send_from_directory('templates', 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory('static', path)

    # Register existing routes
    register_show_routes(app)
    register_backup_routes(app)

    # ✅ Register backup listing API route
    app.register_blueprint(backup_api)

    # ✅ Register load config route
    app.register_blueprint(load_config_bp)
