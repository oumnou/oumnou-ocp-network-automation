from flask import Flask, request, jsonify, send_from_directory
import paramiko
import os

app = Flask(__name__, static_folder='static', static_url_path='')

hostname = "192.168.116.134"
username = "kali"
key_path = os.path.expanduser("~/.ssh/id_rsa")  # Adjust if your key is different


def run_ovs_command(cmd, password=None):
    print(f"[DEBUG] Running command: {cmd}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if os.path.exists(key_path):
        print(f"[DEBUG] Using private key authentication with key: {key_path}")
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh.connect(hostname, username=username, pkey=private_key)
    else:
        print(f"[DEBUG] Using password authentication")
        ssh.connect(hostname, username=username, password=password)

    full_cmd = f"sudo {cmd}"
    print(f"[DEBUG] Full command to execute: {full_cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)

    if password:
        print("[DEBUG] Sending sudo password")
        stdin.write(password + '\n')
        stdin.flush()

    output = stdout.read().decode()
    error = stderr.read().decode()
    print(f"[DEBUG] Command output:\n{output}")
    print(f"[DEBUG] Command error:\n{error}")
    ssh.close()
    return output, error


def clean_ovs_output(raw_output: str) -> str:
    print("[DEBUG] Cleaning raw output")
    lines = raw_output.splitlines()
    cleaned_lines = []

    skip_keys = {
        '_uuid', 'bond_active_slave', 'bond_downdelay', 'bond_fake_iface', 'bond_mode', 'bond_updelay',
        'cvlans', 'external_ids', 'fake_bridge', 'lacp', 'mac', 'other_config', 'protected', 'qos',
        'rstp_statistics', 'rstp_status', 'statistics', 'status', 'tag', 'trunks', 'vlan_mode',
        'cfm_fault', 'cfm_fault_status', 'cfm_flap_count', 'cfm_health', 'cfm_mpid', 'cfm_remote_mpids',
        'cfm_remote_opstate', 'bfd', 'bfd_status', 'error', 'ingress_policing_burst',
        'ingress_policing_kpkts_burst', 'ingress_policing_kpkts_rate', 'ingress_policing_rate',
        'lacp_current', 'link_resets', 'link_speed', 'lldp', 'mtu_request', 'ofport_request',
        'options', 'upcall_errors', 'upcall_packets',
    }

    def line_is_skip(line):
        stripped = line.strip()
        if stripped == "" or stripped == "kali" or stripped.startswith("[sudo]"):
            return True
        if len(stripped) == 36 and all(c in "0123456789abcdef-" for c in stripped.lower()):
            return True
        if ':' in stripped:
            key, val = map(str.strip, stripped.split(':', 1))
            if key in skip_keys and val in ("[]", "{}", ""):
                return True
        return False

    for line in lines:
        if not line_is_skip(line):
            cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    print(f"[DEBUG] Cleaned output:\n{cleaned}")
    return cleaned

def generate_backup_commands(bridge_data, port_data, interface_data):
    commands = []
    
    # Parse port blocks into dict uuid -> name
    port_blocks = []
    current_block = []
    for line in port_data.splitlines():
        if line.strip() == "":
            if current_block:
                port_blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        port_blocks.append(current_block)
    
    port_uuid_to_name = {}
    for block in port_blocks:
        port_uuid = None
        port_name = None
        for line in block:
            line = line.strip()
            if line.startswith("_uuid"):
                port_uuid = line.split(":", 1)[1].strip()
            elif line.startswith("name"):
                port_name = line.split(":", 1)[1].strip().strip('"')
        if port_uuid:
            if port_name:
                port_uuid_to_name[port_uuid] = port_name
            else:
                port_uuid_to_name[port_uuid] = None  # Unknown name

    # Parse interface blocks into dict uuid -> name
    iface_blocks = []
    current_block = []
    for line in interface_data.splitlines():
        if line.strip() == "":
            if current_block:
                iface_blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        iface_blocks.append(current_block)
    
    iface_uuid_to_name = {}
    for block in iface_blocks:
        iface_uuid = None
        iface_name = None
        for line in block:
            line = line.strip()
            if line.startswith("_uuid"):
                iface_uuid = line.split(":", 1)[1].strip()
            elif line.startswith("name"):
                iface_name = line.split(":", 1)[1].strip().strip('"')
        if iface_uuid and iface_name:
            iface_uuid_to_name[iface_uuid] = iface_name

    # Parse bridges and their port UUIDs
    bridges = {}
    current_bridge = None
    for line in bridge_data.splitlines():
        line = line.strip()
        if line.startswith("name"):
            current_bridge = line.split(":", 1)[1].strip().strip('"')
            bridges[current_bridge] = []
        elif line.startswith("ports") and current_bridge:
            ports_str = line.split(":", 1)[1].strip().strip("[]")
            ports = [p.strip() for p in ports_str.split(",") if p.strip()]
            bridges[current_bridge].extend(ports)

    # Build commands
    for br in bridges:
        commands.append(f"ovs-vsctl add-br {br}")
        for port_uuid in bridges[br]:
            # Try port name
            port_name = port_uuid_to_name.get(port_uuid)
            if port_name:
                commands.append(f"ovs-vsctl add-port {br} {port_name}")
            else:
                # Try interface name fallback
                iface_name = iface_uuid_to_name.get(port_uuid)
                if iface_name:
                    commands.append(f"ovs-vsctl add-port {br} {iface_name}")
                else:
                    # Fallback to UUID itself
                    commands.append(f"ovs-vsctl add-port {br} {port_uuid}")

    # Add interface types and tags
    for block in iface_blocks:
        iface_name = None
        iface_type = None
        iface_tag = None
        for line in block:
            line = line.strip()
            if line.startswith("name"):
                iface_name = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("type"):
                iface_type = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("tag"):
                iface_tag = line.split(":", 1)[1].strip()
        if iface_name:
            if iface_type:
                commands.append(f"ovs-vsctl set Interface {iface_name} type={iface_type}")
            if iface_tag:
                commands.append(f"ovs-vsctl set port {iface_name} tag={iface_tag}")

    return "\n".join(commands)

@app.route('/')
def serve_index():
    print("[DEBUG] Serving index.html")
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    print(f"[DEBUG] Serving static file: {path}")
    return send_from_directory('static', path)


@app.route('/api/show_ovs_full', methods=['POST'])
def show_ovs_full():
    print("[DEBUG] /api/show_ovs_full called")
    data = request.json or {}
    password = data.get("password")
    print(f"[DEBUG] Received password: {'***' if password else 'None'}")

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


@app.route('/api/backup_config', methods=['POST'])
def backup_config():
    print("[DEBUG] /api/backup_config called")
    data = request.json or {}
    password = data.get("password")

    cmds = {
        "bridge": "ovs-vsctl list bridge",
        "port": "ovs-vsctl list port",
        "interface": "ovs-vsctl list interface"
    }

    collected = {}
    for key, cmd in cmds.items():
        out, _ = run_ovs_command(cmd, password)
        collected[key] = clean_ovs_output(out)

    backup_text = generate_backup_commands(
        collected["bridge"], collected["port"], collected["interface"]
    )

    backup_path = "ovs_backup.conf"
    try:
        with open(backup_path, "w") as f:
            f.write(backup_text)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({
        "status": "success",
        "message": "Configuration sauvegardée.",
        "backup_file": backup_path,
        "commands": backup_text
    })


# Optional: allow users to download the saved config
@app.route('/api/download_backup', methods=['GET'])
def download_backup():
    print("[DEBUG] /api/download_backup called")
    return send_from_directory('.', 'ovs_backup.conf', as_attachment=True)


if __name__ == '__main__':
    print("[DEBUG] Starting Flask app")
    app.run(debug=True, host='0.0.0.0', port=5000)
