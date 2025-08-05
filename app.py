from flask import Flask, request, jsonify, send_from_directory
import paramiko
import os

app = Flask(__name__, static_folder='static', static_url_path='')

hostname = "192.168.116.134"
username = "kali"
key_path = os.path.expanduser("~/.ssh/id_rsa")  # Adjust as needed

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
        # Skip shell prompt or sudo password prompt lines
        if stripped == "" or stripped == "kali" or stripped.startswith("[sudo]"):
            return True
        # Skip UUID lines
        if len(stripped) == 36 and all(c in "0123456789abcdef-" for c in stripped.lower()):
            return True
        # Skip empty keys from skip_keys
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
        print(f"[DEBUG] Executing command: {cmd}")
        output, error = run_ovs_command(cmd, password=password)
        results[cmd] = {
            "output": clean_ovs_output(output),
            "error": error
        }
        print(f"[DEBUG] Finished command: {cmd}")

    print("[DEBUG] Returning results as JSON")
    return jsonify(results)

@app.route('/')
def serve_index():
    print("[DEBUG] Serving index.html")
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    print(f"[DEBUG] Serving static file: {path}")
    return send_from_directory('static', path)

if __name__ == '__main__':
    print("[DEBUG] Starting Flask app")
    app.run(debug=True, host='0.0.0.0', port=5000)
