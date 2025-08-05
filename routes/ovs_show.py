from flask import request, jsonify
from services.ssh_utils import run_ovs_command, clean_ovs_output

def register_show_routes(app):
    @app.route('/api/show_ovs_full', methods=['POST'])
    def show_ovs_full():
        data = request.json or {}
        print("data",data)
        password = data.get("password")
        switch_name = data.get("switch_name", "default_switch").strip().replace(" ", "_")

        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400

        commands = {
            "ovs-vsctl show": None,
            "ovs-vsctl list bridge": None,
            "ovs-vsctl list port": None,
            "ovs-vsctl list interface": None
        }

        results = {}
        for cmd in commands:
            output, error = run_ovs_command(cmd, password=password)
            print(f"Command: {cmd}")
            print(f"Output: {output[:200]}")  # print first 200 chars max
            print(f"Error: {error}")
            results[cmd] = {
                "output": clean_ovs_output(output),
                "error": error or None
            }

        return jsonify({
            "success": True,
            "switch_name": switch_name,
            "results": results
        })
