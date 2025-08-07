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

        # 🧠 Step 1: First verify the bridge exists
        bridge_check_cmd = f"ovs-vsctl br-exists {switch_name}"
        _, check_err = run_ovs_command(bridge_check_cmd, password=password)
        
        if check_err and "does not exist" in check_err.lower():
            return jsonify({
                "success": False, 
                "error": f"Bridge '{switch_name}' does not exist. Available bridges can be seen with 'ovs-vsctl list-br'"
            }), 400

        # 🧠 Step 2: Get list of ports on the given bridge
        raw_ports, err = run_ovs_command(f"ovs-vsctl list-ports {switch_name}", password=password)
        
        if err and ("no bridge named" in err.lower() or "does not exist" in err.lower()):
            return jsonify({
                "success": False, 
                "error": f"Bridge '{switch_name}' not found. Error: {err}"
            }), 400

        # Clean and validate port output
        cleaned_ports = clean_ovs_output(raw_ports)
        if not cleaned_ports.strip():
            # No ports found, but bridge exists
            port_list = []
        else:
            port_list = [p.strip() for p in cleaned_ports.splitlines() if p.strip()]

        # Filter out any error messages that might have slipped through
        valid_ports = []
        for port in port_list:
            if "ovs-vsctl:" in port.lower() or "error:" in port.lower() or "no bridge" in port.lower():
                continue  # Skip error messages
            valid_ports.append(port)

        ports_data = []
        interfaces_data = []

        # 🧠 Step 3: For each valid port, get its interface type
        for port in valid_ports:
            if not port:
                continue
                
            # Get interface type for the port
            iface_type_cmd = f"ovs-vsctl get Interface {port} type"
            iface_type_raw, iface_err = run_ovs_command(iface_type_cmd, password=password)
            
            if iface_err:
                # If there's an error getting the type, set it as empty
                iface_type = ""
            else:
                iface_type = clean_ovs_output(iface_type_raw).strip().strip('"')
                # If the result is still an error message, set as empty
                if "ovs-vsctl:" in iface_type.lower() or "error:" in iface_type.lower():
                    iface_type = ""

            ports_data.append({"name": port, "type": iface_type})
            interfaces_data.append({"name": port, "type": iface_type})

        # 🧠 Step 4: Also get bridge information
        bridge_info_cmd = f"ovs-vsctl get Bridge {switch_name} datapath_id"
        datapath_raw, dp_err = run_ovs_command(bridge_info_cmd, password=password)
        
        datapath_id = ""
        if not dp_err:
            datapath_id = clean_ovs_output(datapath_raw).strip().strip('"')
            if "ovs-vsctl:" in datapath_id.lower() or "error:" in datapath_id.lower():
                datapath_id = ""

        # 🧠 Step 5: Build YAML structure
        yaml_data = {
            "bridges": [{
                "name": switch_name,
                "datapath_id": datapath_id,
                "ports": ports_data
            }],
            "interfaces": interfaces_data
        }

        # 🧠 Step 6: Save YAML file
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{switch_name}_backup_{timestamp}.yaml"
        filepath = os.path.join(BACKUP_FOLDER, filename)

        try:
            with open(filepath, "w") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, indent=2)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to save backup file: {str(e)}"
            }), 500

        return jsonify({
            "success": True,
            "message": f"Backup saved to {filename}",
            "file": filename,
            "ports_found": len(valid_ports),
            "bridge_exists": True
        })