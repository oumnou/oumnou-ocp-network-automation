import paramiko
import os

hostname = "192.168.116.134"
username = "kali"
key_path = os.path.expanduser("~/.ssh/id_rsa")

def run_ovs_command(cmd, password=None):
    """
    Connects via SSH and runs a command prefixed with sudo.
    Uses private key authentication if available, otherwise password.
    Returns (stdout, stderr).
    """
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
        # Send sudo password if needed
        stdin.write(password + '\n')
        stdin.flush()

    output = stdout.read().decode()
    error = stderr.read().decode()
    ssh.close()

    return output, error

def clean_ovs_output(raw_output: str) -> str:
    """
    Cleans the OVS output by filtering out unneeded lines:
    - username line 'kali'
    - sudo prompts
    - UUID lines (36 char hex + hyphen)
    - empty lines
    """
    lines = raw_output.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == "kali" or stripped.startswith("[sudo]"):
            continue
        if len(stripped) == 36 and all(c in "0123456789abcdef-" for c in stripped.lower()):
            continue
        if stripped == "":
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)
