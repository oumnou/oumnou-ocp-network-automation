from flask import Flask, request, jsonify, send_from_directory
import paramiko
import os

app = Flask(__name__, static_folder='static', static_url_path='')

hostname = "192.168.116.134"
username = "kali"
key_path = os.path.expanduser("~/.ssh/id_rsa")  # Adjust as needed

def run_ovs_command(cmd, password=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if os.path.exists(key_path):
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh.connect(hostname, username=username, pkey=private_key)
    else:
        ssh.connect(hostname, username=username, password=password)

    full_cmd = f"sudo {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)

    if password:
        stdin.write(password + '\n')
        stdin.flush()

    output = stdout.read().decode()
    error = stderr.read().decode()
    ssh.close()
    return output, error

def clean_ovs_output(raw_output: str) -> str:
    lines = raw_output.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip unwanted lines
        if stripped == "kali":
            continue
        if stripped.startswith("[sudo]"):
            continue
        # Skip UUID lines (36 chars hex with dashes)
        if len(stripped) == 36 and all(c in "0123456789abcdef-" for c in stripped.lower()):
            continue
        if stripped == "":
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

@app.route('/api/show_ovs', methods=['POST'])
def show_ovs():
    data = request.json or {}
    password = data.get("password")  # Optional if using key auth

    cmd = "ovs-vsctl show"
    output, error = run_ovs_command(cmd, password=password)
    cleaned_output = clean_ovs_output(output)

    return jsonify({"output": cleaned_output, "error": error})

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

# Optional: serve other static files (CSS, JS, etc)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
