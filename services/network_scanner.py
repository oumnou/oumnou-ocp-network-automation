# services/network_scanner.py

import subprocess
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko
import socket

class NetworkScanner:
    def __init__(self):
        self.open_ports = [22, 23, 80, 443, 161, 830]  # Common switch ports
    
    def scan_network(self, network_range):
        """
        Scan network range for active hosts using nmap
        Args:
            network_range (str): Network range like "192.168.1.0/24"
        Returns:
            list: List of discovered hosts with details
        """
        try:
            # Basic host discovery with nmap
            cmd = [
                'nmap', 
                '-sn',  # Ping scan only
                '--host-timeout', '10s',
                network_range
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return {'error': f'Nmap scan failed: {result.stderr}'}
            
            # Parse nmap output to extract IP addresses
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            discovered_ips = re.findall(ip_pattern, result.stdout)
            
            # Remove duplicates and filter valid IPs
            unique_ips = list(set(discovered_ips))
            valid_ips = [ip for ip in unique_ips if self._is_valid_ip(ip)]
            
            # Get detailed info for each IP
            hosts = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self._get_host_details, ip): ip for ip in valid_ips}
                
                for future in as_completed(futures):
                    host_info = future.result()
                    if host_info:
                        hosts.append(host_info)
            
            return {'hosts': sorted(hosts, key=lambda x: x['ip'])}
            
        except subprocess.TimeoutExpired:
            return {'error': 'Network scan timed out'}
        except FileNotFoundError:
            return {'error': 'Nmap not found. Please install nmap: sudo apt-get install nmap'}
        except Exception as e:
            return {'error': f'Scan error: {str(e)}'}
    
    def _is_valid_ip(self, ip):
        """Validate IP address format"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            return True
        except:
            return False
    
    def _get_host_details(self, ip):
        """Get detailed information about a host"""
        try:
            # Skip localhost and broadcast
            if ip.endswith('.0') or ip.endswith('.255') or ip == '127.0.0.1':
                return None
            
            host_info = {
                'ip': ip,
                'hostname': self._get_hostname(ip),
                'open_ports': self._scan_ports(ip),
                'is_switch_candidate': False,
                'ssh_available': False,
                'device_type': 'Unknown'
            }
            
            # Check if SSH is available
            if 22 in host_info['open_ports']:
                host_info['ssh_available'] = True
                host_info['device_type'] = self._identify_device_type(ip)
            
            # Determine if this could be a switch
            switch_indicators = [
                22 in host_info['open_ports'],  # SSH
                161 in host_info['open_ports'], # SNMP
                any(port in host_info['open_ports'] for port in [80, 443, 830])  # Web/NETCONF
            ]
            
            if any(switch_indicators):
                host_info['is_switch_candidate'] = True
            
            return host_info
            
        except Exception as e:
            return None
    
    def _get_hostname(self, ip):
        """Try to resolve hostname for IP"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return ip
    
    def _scan_ports(self, ip, timeout=2):
        """Scan common switch ports"""
        open_ports = []
        
        for port in self.open_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except:
                pass
        
        return open_ports
    
    def _identify_device_type(self, ip):
        """Try to identify device type via SSH banner or other methods"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, 22))
            
            # Get SSH banner
            banner = sock.recv(1024).decode('utf-8', errors='ignore').lower()
            sock.close()
            
            # Identify based on SSH banner
            if 'openssh' in banner:
                if any(keyword in banner for keyword in ['linux', 'ubuntu', 'debian']):
                    return 'Linux Server/Switch'
                else:
                    return 'SSH Server'
            elif 'cisco' in banner:
                return 'Cisco Device'
            elif 'juniper' in banner:
                return 'Juniper Device'
            else:
                return 'Network Device'
                
        except:
            return 'Unknown'
    
    def test_switch_connectivity(self, ip, username='kali', password=None):
        """Test if we can connect to a switch and run OVS commands"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try to connect
            ssh.connect(ip, username=username, password=password, timeout=10)
            
            # Test OVS command
            stdin, stdout, stderr = ssh.exec_command('sudo ovs-vsctl show', get_pty=True)
            
            if password:
                stdin.write(password + '\n')
                stdin.flush()
            
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            ssh.close()
            
            # Check if OVS is available
            if 'ovs-vsctl' in error and 'command not found' in error:
                return {'success': False, 'error': 'Open vSwitch not found on this host'}
            elif output or not error:
                return {'success': True, 'message': 'OVS connection successful'}
            else:
                return {'success': False, 'error': f'Connection failed: {error}'}
                
        except paramiko.AuthenticationException:
            return {'success': False, 'error': 'Authentication failed'}
        except paramiko.SSHException as e:
            return {'success': False, 'error': f'SSH error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}