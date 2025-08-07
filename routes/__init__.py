# routes/__init__.py

from .ovs_show import register_show_routes
from .ovs_backup import register_backup_routes
from .ovs_load_config import load_config_bp
from .api_backups import backup_api
from .network_scan import network_scan_bp  # ✅ Import network scanner
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

    # ✅ Register all blueprints
    app.register_blueprint(backup_api)
    app.register_blueprint(load_config_bp)
    app.register_blueprint(network_scan_bp)  # ✅ Register network scanner routes