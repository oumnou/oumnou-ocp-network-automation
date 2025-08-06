from flask import request, jsonify
from datetime import datetime
import os
import yaml
from services.ssh_utils import run_ovs_command, clean_ovs_output

BACKUP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backup')

def register_backup_routes(app):
    @app.route('/api/backup_config', methods=['POST'])
    def backup_config():
        data = request.json or {}
        password = data.get("password")
        switch_name = data.get("switch")

        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400
        if not switch_name:
            return jsonify({"success": False, "error": "Switch name is required."}), 400

        # 🧠 Step 1: Get list of ports on the given bridge
        raw_ports, err = run_ovs_command(f"ovs-vsctl list-ports {switch_name}", password=password)
        if err:
            return jsonify({"success": False, "error": f"Error getting ports: {err}"}), 500

        port_list = clean_ovs_output(raw_ports).splitlines()

        ports_data = []
        interfaces_data = []

        # 🧠 Step 2: For each port, get its interface type
        for port in port_list:
            port = port.strip()
            if not port:
                continue
            # Get interface type for the port
            iface_type_cmd = f"ovs-vsctl get Interface {port} type"
            iface_type_raw, err = run_ovs_command(iface_type_cmd, password=password)
            if err:
                iface_type = ""
            else:
                iface_type = clean_ovs_output(iface_type_raw).strip().strip('"')

            ports_data.append({"name": port, "type": iface_type})
            interfaces_data.append({"name": port, "type": iface_type})

        # 🧠 Step 3: Build YAML structure
        yaml_data = {
            "bridges": [{
                "name": switch_name,
                "ports": ports_data
            }],
            "interfaces": interfaces_data
        }

        # 🧠 Step 4: Save YAML file
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{switch_name}_backup_{timestamp}.yaml"
        filepath = os.path.join(BACKUP_FOLDER, filename)

        with open(filepath, "w") as f:
            yaml.dump(yaml_data, f, default_flow_style=False)

        return jsonify({
            "success": True,
            "message": f"Backup saved to {filename}",
            "file": filename
        })
