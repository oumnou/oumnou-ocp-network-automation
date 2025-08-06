from flask import request, jsonify
from services.ssh_utils import run_ovs_command, clean_ovs_output
import yaml
import os
import re

def parse_ovs_list(raw_output):
    """
    Parses 'ovs-vsctl list <table>' output blocks separated by blank lines.
    Returns a list of dicts, each dict corresponds to one block.
    """
    blocks = []
    current_block = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if line == "":
            if current_block:
                blocks.append(current_block)
                current_block = {}
        else:
            m = re.match(r"(\S+)\s*:\s*(.*)", line)
            if m:
                key, val = m.group(1), m.group(2)
                current_block[key] = val
            else:
                # Lines not matching key: value are ignored here
                pass
    if current_block:
        blocks.append(current_block)
    return blocks

def register_show_routes(app):
    @app.route('/api/show_ovs_full', methods=['POST'])
    def show_ovs_full():
        data = request.json or {}
        print("data", data)
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
        raw_outputs = {}

        for cmd in commands:
            output, error =run_ovs_command('ovs-vsctl show', password='kali')

            print(f"Command: {cmd}")
            print(f"Output: {output[:200]}")  # first 200 chars max
            print(f"Error: {error}")
            results[cmd] = {
                "output": clean_ovs_output(output),
                "error": error or None
            }
            raw_outputs[cmd] = output  # keep raw outputs for parsing

        # Parse bridge, port, interface outputs to structured data
        bridges = parse_ovs_list(raw_outputs["ovs-vsctl list bridge"])
        ports = parse_ovs_list(raw_outputs["ovs-vsctl list port"])
        interfaces = parse_ovs_list(raw_outputs["ovs-vsctl list interface"])

        # Build quick lookups by name
        interfaces_by_name = {iface.get("name"): iface for iface in interfaces if "name" in iface}
        ports_by_name = {port.get("name"): port for port in ports if "name" in port}

        switch_data = {
            "switch_name": switch_name,
            "bridges": []
        }

        for bridge in bridges:
            bridge_name = bridge.get("name")
            bridge_ports = []

            # Find ports associated with this bridge (heuristic: check "name" contains bridge_name or refine as needed)
            for port_name, port in ports_by_name.items():
                # The 'fake_bridge' field sometimes can be used or external_ids
                # Here a simple heuristic: port name starts with bridge name or port in bridge's ports list
                # For now, just add all ports - you can improve logic later
                # Alternatively, you can check if port UUID appears in bridge 'ports' list if available

                bridge_ports.append({
                    "name": port_name,
                    "tag": port.get("tag"),
                    "interfaces": []
                })

            bridge_data = {
                "name": bridge_name,
                "datapath_id": bridge.get("datapath_id"),
                "ports": bridge_ports
            }
            switch_data["bridges"].append(bridge_data)

        # Save to YAML file in backups/
        backup_dir = "backup"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        backup_path = os.path.join(backup_dir, f"{switch_name}.yaml")

        with open(backup_path, "w") as f:
            yaml.safe_dump(switch_data, f)

        print(f"Switch config saved to {backup_path}")

        return jsonify({
            "success": True,
            "switch_name": switch_name,
            "results": results
        })
