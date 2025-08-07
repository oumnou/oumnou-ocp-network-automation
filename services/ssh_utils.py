import paramiko
import os

key_path = os.path.expanduser("~/.ssh/id_rsa")

def run_ovs_command(cmd, hostname='192.168.116.135', username='kali', password=None):
    """
    Connects via SSH and runs a command prefixed with sudo on the given host.
    Uses private key authentication if available, otherwise password.
    Returns (stdout, stderr).
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
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
        
        # Check if the output contains error messages
        if "ovs-vsctl:" in output and ("error" in output.lower() or "does not exist" in output.lower() or "no bridge named" in output.lower()):
            # Move error messages from stdout to stderr
            error = output if not error else error + "\n" + output
            output = ""
        
        ssh.close()
        return output, error
        
    except Exception as e:
        try:
            ssh.close()
        except:
            pass
        return "", f"SSH connection error: {str(e)}"

def clean_ovs_output(raw_output: str) -> str:
    """
    Cleans the OVS output by filtering out unneeded lines:
    - username line 'kali'
    - sudo prompts
    - UUID lines (36 char hex + hyphen)
    - empty lines
    - error messages
    """
    if not raw_output:
        return ""
        
    lines = raw_output.splitlines()
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip common noise
        if stripped == "kali" or stripped.startswith("[sudo]"):
            continue
            
        # Skip UUID lines
        if len(stripped) == 36 and all(c in "0123456789abcdef-" for c in stripped.lower()):
            continue
            
        # Skip empty lines
        if stripped == "":
            continue
            
        # Skip error messages that might appear in stdout
        if any(error_marker in stripped.lower() for error_marker in [
            "ovs-vsctl: no bridge named",
            "ovs-vsctl: no port named", 
            "ovs-vsctl: no interface named",
            "does not exist",
            "does not contain a column"
        ]):
            continue
            
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)