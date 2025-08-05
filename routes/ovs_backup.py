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

        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400

        # 1. Get all bridges (switches) with their details
        raw_bridges, err = run_ovs_command("ovs-vsctl list bridge", password=password)
        if err:
            return jsonify({"success": False, "error": f"Error fetching bridges: {err}"}), 500

        raw_ports, err = run_ovs_command("ovs-vsctl list port", password=password)
        if err:
            return jsonify({"success": False, "error": f"Error fetching ports: {err}"}), 500

        raw_interfaces, err = run_ovs_command("ovs-vsctl list interface", password=password)
        if err:
            return jsonify({"success": False, "error": f"Error fetching interfaces: {err}"}), 500

        raw_bridges = clean_ovs_output(raw_bridges)
        raw_ports = clean_ovs_output(raw_ports)
        raw_interfaces = clean_ovs_output(raw_interfaces)

        # 2. Parse raw_bridges to get list of switch names
        # Each bridge block starts with "name: ..."
        bridges = []
        current_bridge = None
        for line in raw_bridges.splitlines():
            line = line.strip()
            if line.startswith("name"):
                current_bridge = line.split(":", 1)[1].strip().strip('"')
                bridges.append(current_bridge)

        if not bridges:
            return jsonify({"success": False, "error": "No switches found to backup."}), 404

        # Ensure backup folder exists
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)

        backup_files = []

        # 3. For each bridge, generate backup commands and save file
        for bridge_name in bridges:
            # Filter bridge data block for only this bridge
            bridge_blocks = []
            current_block = []
            inside_current_bridge = False
            for line in raw_bridges.splitlines():
                if line.strip().startswith("name"):
                    if current_block:
                        bridge_blocks.append(current_block)
                        current_block = []
                    if bridge_name in line:
                        inside_current_bridge = True
                    else:
                        inside_current_bridge = False
                if inside_current_bridge:
                    current_block.append(line)
            if current_block:
                bridge_blocks.append(current_block)

            bridge_block_text = "\n".join([line for block in bridge_blocks for line in block])

            # You can just reuse the full port and interface data (or optimize later)
            commands = generate_backup_commands(bridge_block_text, raw_ports, raw_interfaces)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{bridge_name}_backup_{timestamp}.sh"
            filepath = os.path.join(BACKUP_FOLDER, filename)

            with open(filepath, "w") as f:
                f.write("#!/bin/bash\n")
                f.write(commands)

            backup_files.append(filename)

        return jsonify({
            "success": True,
            "message": f"Backups saved for {len(backup_files)} switches.",
            "files": backup_files
        })
