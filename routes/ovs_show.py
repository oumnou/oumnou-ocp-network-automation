from flask import request, jsonify
from services.ssh_utils import run_ovs_command, clean_ovs_output

def register_show_routes(app):
    @app.route('/api/show_ovs_full', methods=['POST'])
    def show_ovs_full():
        data = request.json or {}
        password = data.get("password")
        
        commands = [
            "ovs-vsctl show",
            "ovs-vsctl list bridge",
            "ovs-vsctl list port",
            "ovs-vsctl list interface",
        ]

        results = {}
        for cmd in commands:
            output, error = run_ovs_command(cmd, password=password)
            results[cmd] = {
                "output": clean_ovs_output(output),
                "error": error
            }

        return jsonify(results)
