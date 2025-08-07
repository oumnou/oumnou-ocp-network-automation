# services/network_scanner.py

import subprocess
import re
import json
import socket
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko
import logging
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class NetworkScanner:
    def __init__(self):
        self.open_ports = [22, 23, 80, 443, 161, 830]  # Common switch ports
        self.timeout = 2
    
    def check_nmap_installed(self):
        """Check if nmap is installed on the system"""
        try:
            result = subprocess.run(['nmap', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def scan_network(self, network_range):
        """
        Scan network range for active hosts
        Args:
            network_range (str): Network range like "192.168.1.0/24"
        Returns:
            dict: Results with hosts or error
        """
        try:
            logger.info(f"Starting network scan for {network_range}")
            
            # Validate network range
            try:
                network = ipaddress.IPv4Network(network_range, strict=False)
            except ValueError as e:
                return {'error': f'Format de réseau invalide: {str(e)}'}
            
            # Check if nmap is available
            if self.check_nmap_installed():
                logger.info("Using nmap for network scan")
                return self._scan_with_nmap(network_range)
            else:
                logger.info("Nmap not available, using Python ping scan")
                return self._scan_with_ping(network)
                
        except Exception as e:
            logger.error(f"Network scan error: {str(e)}")
            return {'error': f'Erreur lors du scan: {str(e)}'}
    
    def _scan_with_nmap(self, network_range):
        """Scan using nmap if available"""
        try:
            # Basic host discovery with nmap
            cmd = [
                'nmap', 
                '-sn',  # Ping scan only
                '--host-timeout', '10s',
                '-T4',  # Faster timing
                network_range
            ]
            
            logger.info(f"Running nmap command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Nmap failed with return code {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                return {'error': f'Nmap scan failed: {result.stderr}'}
            
            # Parse nmap output to extract IP addresses
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            discovered_ips = re.findall(ip_pattern, result.stdout)
            
            # Remove duplicates and filter valid IPs
            unique_ips = list(set(discovered_ips))
            valid_ips = [ip for ip in unique_ips if self._is_valid_ip(ip)]
            
            logger.info(f"Found {len(valid_ips)} valid IPs")
            
            # Get detailed info for each IP
            return self._get_host_details_batch(valid_ips)
            
        except subprocess.TimeoutExpired:
            return {'error': 'Network scan timed out'}
        except Exception as e:
            logger.error(f"Nmap scan error: {str(e)}")
            return {'error': f'Nmap scan error: {str(e)}'}
    
    def _scan_with_ping(self, network):
        """Fallback ping scan using Python"""
        try:
            logger.info(f"Performing ping scan on {network}")
            hosts = []
            
            # Generate list of IPs to scan (limit to reasonable size)
            ip_list = list(network.hosts())
            if len(ip_list) > 254:  # Limit for /24 or smaller
                ip_list = ip_list[:254]
            
            # Ping each host
            active_ips = []
            with ThreadPoolExecutor(max_workers=50) as executor:
                future_to_ip = {executor.submit(self._ping_host, str(ip)): str(ip) 
                               for ip in ip_list}
                
                for future in as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    try:
                        if future.result():
                            active_ips.append(ip)
                    except Exception as e:
                        logger.debug(f"Ping failed for {ip}: {e}")
            
            logger.info(f"Found {len(active_ips)} active IPs via ping")
            
            # Get detailed info for active IPs
            return self._get_host_details_batch(active_ips)
            
        except Exception as e:
            logger.error(f"Ping scan error: {str(e)}")
            return {'error': f'Ping scan error: {str(e)}'}
    
    def _ping_host(self, ip):
        """Ping a single host"""
        try:
            # Use system ping command
            import platform
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            cmd = ['ping', param, '1', '-W', '2000', ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _get_host_details_batch(self, ip_list):
        """Get detailed information for multiple hosts"""
        hosts = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self._get_host_details, ip): ip for ip in ip_list}
            
            for future in as_completed(futures):
                try:
                    host_info = future.result()
                    if host_info:
                        hosts.append(host_info)
                except Exception as e:
                    logger.debug(f"Failed to get host details: {e}")
        
        return {'hosts': sorted(hosts, key=lambda x: x['ip'])}
    
    def _is_valid_ip(self, ip):
        """Validate IP address format"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            # Skip localhost, broadcast, and network addresses
            if ip.endswith('.0') or ip.endswith('.255') or ip == '127.0.0.1':
                return False
            return True
        except:
            return False
    
    def _get_host_details(self, ip):
        """Get detailed information about a host"""
        try:
            logger.debug(f"Getting details for {ip}")
            
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
            logger.debug(f"Error getting details for {ip}: {e}")
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
        """Try to identify device type via SSH banner"""
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
            logger.info(f"Testing switch connectivity to {ip}")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try to connect
            ssh.connect(ip, username=username, password=password, timeout=10)
            
            # Test basic connectivity first
            stdin, stdout, stderr = ssh.exec_command('echo "test"', get_pty=True)
            output = stdout.read().decode().strip()
            
            if 'test' not in output:
                ssh.close()
                return {'success': False, 'error': 'SSH connection failed - no response'}
            
            # Test OVS command
            stdin, stdout, stderr = ssh.exec_command('sudo ovs-vsctl show', get_pty=True)
            
            if password:
                stdin.write(password + '\n')
                stdin.flush()
            
            # Wait a bit for command to execute
            time.sleep(2)
            
            output = stdout.read().decode()
            error = stderr.read().decode()
            
            ssh.close()
            
            # Check if OVS is available
            if 'command not found' in error or 'ovs-vsctl: not found' in error:
                return {
                    'success': False, 
                    'error': 'Open vSwitch not found on this host',
                    'ssh_works': True
                }
            elif 'permission denied' in error.lower():
                return {
                    'success': False, 
                    'error': 'Permission denied - check sudo access',
                    'ssh_works': True
                }
            elif output or not error:
                return {
                    'success': True, 
                    'message': 'OVS connection successful',
                    'ssh_works': True
                }
            else:
                return {
                    'success': False, 
                    'error': f'OVS test failed: {error}',
                    'ssh_works': True
                }
                
        except paramiko.AuthenticationException:
            return {'success': False, 'error': 'Authentication failed'}
        except paramiko.SSHException as e:
            return {'success': False, 'error': f'SSH error: {str(e)}'}
        except Exception as e:
            logger.error(f"Switch connectivity test error: {str(e)}")
            return {'success': False, 'error': f'Connection error: {str(e)}'}
    
    def quick_scan(self, base_ip='192.168.1.1'):
        """Quick scan based on provided base IP"""
        try:
            logger.info(f"Quick scan from base IP: {base_ip}")
            
            # Extract subnet from base IP
            ip_parts = base_ip.split('.')
            if len(ip_parts) != 4:
                return {'error': 'Format IP invalide'}

            network_range = f"{'.'.join(ip_parts[:3])}.0/24"
            
            # Perform the scan
            result = self.scan_network(network_range)
            
            if 'error' in result:
                return result
            
            return {
                'success': True,
                'network_scanned': network_range,
                'hosts': result['hosts'],
                'total_found': len(result['hosts']),
                'switch_candidates': len([
                    h for h in result['hosts'] if h.get('is_switch_candidate')
                ])
            }
            
        except Exception as e:
            logger.error(f"Quick scan error: {str(e)}")
            return {'error': f'Erreur lors du scan rapide: {str(e)}'}