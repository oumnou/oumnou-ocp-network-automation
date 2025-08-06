import os
from datetime import datetime
import yaml
from flask import request, jsonify
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

        raw_bridges, err = run_ovs_command("ovs-vsctl list bridge", password=password,)
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

        # Parse bridge blocks
        bridges = []
        current_bridge = None
        current_block = []
        for line in raw_bridges.splitlines():
            line = line.strip()
            if line.startswith("name"):
                if current_bridge is not None:
                    bridges.append({"name": current_bridge, "block": current_block})
                current_bridge = line.split(":", 1)[1].strip().strip('"')
                current_block = [line]
            else:
                if current_bridge:
                    current_block.append(line)
        if current_bridge is not None:
            bridges.append({"name": current_bridge, "block": current_block})

        # Filter only the specified switch
        selected_bridge = next((b for b in bridges if b["name"] == switch_name), None)
        if not selected_bridge:
            return jsonify({"success": False, "error": f"Switch '{switch_name}' not found."}), 404

        # Parse ports
        ports = {}
        current_port = None
        current_block = []
        for line in raw_ports.splitlines():
            line = line.strip()
            if line.startswith("name"):
                if current_port is not None:
                    ports[current_port] = parse_ovs_block(current_block)
                current_port = line.split(":", 1)[1].strip().strip('"')
                current_block = [line]
            else:
                if current_port:
                    current_block.append(line)
        if current_port is not None:
            ports[current_port] = parse_ovs_block(current_block)

        # Parse interfaces
        interfaces = {}
        current_iface = None
        current_block = []
        for line in raw_interfaces.splitlines():
            line = line.strip()
            if line.startswith("name"):
                if current_iface is not None:
                    interfaces[current_iface] = parse_ovs_block(current_block)
                current_iface = line.split(":", 1)[1].strip().strip('"')
                current_block = [line]
            else:
                if current_iface:
                    current_block.append(line)
        if current_iface is not None:
            interfaces[current_iface] = parse_ovs_block(current_block)

        # Collect ports associated with this switch
        selected_ports = []
        for port_name, port_info in ports.items():
            if port_info.get("bridge") == switch_name:
                selected_ports.append(port_name)

        # Collect interfaces associated with the selected ports
        selected_ifaces = []
        for iface_name, iface_info in interfaces.items():
            if iface_name in selected_ports:  # often port and iface names match
                selected_ifaces.append({"name": iface_name, "type": iface_info.get("type", "")})

        # Build YAML
        yaml_data = {
            "bridges": [{
                "name": switch_name,
                "ports": [{"name": p} for p in selected_ports]
            }],
            "interfaces": selected_ifaces
        }

        # Save
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

def parse_ovs_block(block_lines):
    """
    Parse lines of 'ovs-vsctl list' block into key:value dict.
    Assumes lines like 'key: value'.
    """
    result = {}
    for line in block_lines:
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"')
            result[key] = val
    return result
