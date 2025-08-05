import paramiko
import getpass

hostname = "192.168.116.134"   # Kali IP
username = "kali"
password = getpass.getpass("Enter SSH password: ")

def run_ovs_show():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password)
    
    # Run ovs-vsctl show (use sudo if required)
    cmd = "sudo ovs-vsctl show"
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    
    # If sudo asks for password, send it
    stdin.write(password + '\n')
    stdin.flush()
    
    output = stdout.read().decode()
    error = stderr.read().decode()
    
    ssh.close()
    
    if error:
        print("Error:", error)
    return output

if __name__ == "__main__":
    ovs_output = run_ovs_show()
    print("Open vSwitch configuration:\n", ovs_output)
