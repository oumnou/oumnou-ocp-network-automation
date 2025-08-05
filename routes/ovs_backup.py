import os
from datetime import datetime
from flask import request, jsonify
from services.ssh_utils import run_ovs_command, clean_ovs_output
from services.backup_utils import generate_backup_commands

BACKUP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backup')

def register_backup_routes(app):
    @app.route('/api/backup_config', methods=['POST'])
    def backup_config():
        data = request.json or {}
        password = data.get("password")

        # Run SSH commands
        bridge_output, _ = run_ovs_command("ovs-vsctl list bridge", password=password)
        port_output, _ = run_ovs_command("ovs-vsctl list port", password=password)
        interface_output, _ = run_ovs_command("ovs-vsctl list interface", password=password)

        # Clean output
        bridge_output = clean_ovs_output(bridge_output)
        port_output = clean_ovs_output(port_output)
        interface_output = clean_ovs_output(interface_output)

        # Generate backup commands
        commands = generate_backup_commands(bridge_output, port_output, interface_output)

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ovs_backup_{timestamp}.sh"
        filepath = os.path.join(BACKUP_FOLDER, filename)

        try:
            with open(filepath, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(commands)

            return jsonify({
                "success": True,
                "message": f"Backup saved as {filename}",
                "filename": filename,
                "commands": commands
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
