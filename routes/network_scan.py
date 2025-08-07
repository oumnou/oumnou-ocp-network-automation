# routes/network_scan.py

from flask import Blueprint, request, jsonify
from services.network_scanner import NetworkScanner
import re
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

network_scan_bp = Blueprint('network_scan', __name__)
scanner = NetworkScanner()

@network_scan_bp.route('/api/scan_network', methods=['POST'])
def scan_network():
    """Scan network range for potential switches"""
    try:
        logger.info("Received network scan request")
        data = request.json or {}
        network_range = data.get('network_range')

        if not network_range:
            logger.warning("No network range provided")
            return jsonify({
                'success': False,
                'error': 'La plage réseau est requise (ex: 192.168.1.0/24)'
            }), 400

        # Validate network range format (e.g., 192.168.1.0/24)
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$', network_range):
            logger.warning(f"Invalid network range format: {network_range}")
            return jsonify({
                'success': False,
                'error': 'Format de plage réseau invalide. Format attendu : 192.168.1.0/24'
            }), 400

        logger.info(f"Starting network scan for: {network_range}")
        
        # Perform network scan
        result = scanner.scan_network(network_range)

        if 'error' in result:
            logger.error(f"Network scan failed: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

        logger.info(f"Network scan completed. Found {len(result['hosts'])} hosts")
        
        return jsonify({
            'success': True,
            'hosts': result['hosts'],
            'total_found': len(result['hosts']),
            'switch_candidates': len([
                h for h in result['hosts'] if h.get('is_switch_candidate')
            ])
        })

    except Exception as e:
        logger.error(f"Network scan route error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f"Échec du scan : {str(e)}"
        }), 500

@network_scan_bp.route('/api/test_switch', methods=['POST'])
def test_switch():
    """Test SSH connectivity and check if it's an OVS switch"""
    try:
        logger.info("Received switch test request")
        data = request.json or {}
        ip = data.get('ip')
        username = data.get('username', 'kali')  # default username
        password = data.get('password')

        if not ip:
            return jsonify({
                'success': False,
                'error': 'Adresse IP requise'
            }), 400

        if not password:
            return jsonify({
                'success': False,
                'error': 'Mot de passe requis pour le test de connexion'
            }), 400

        logger.info(f"Testing switch connectivity for: {ip}")
        
        # Run the connectivity test
        result = scanner.test_switch_connectivity(ip, username, password)
        
        logger.info(f"Switch test result: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Switch test route error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f"Échec du test : {str(e)}"
        }), 500

@network_scan_bp.route('/api/quick_scan', methods=['POST'])
def quick_scan():
    """Quick scan based on provided base IP (e.g., 192.168.1.1)"""
    try:
        logger.info("Received quick scan request")
        data = request.json or {}
        base_ip = data.get('base_ip', '192.168.1.1')

        logger.info(f"Starting quick scan from base IP: {base_ip}")
        
        # Perform the scan using the scanner's quick_scan method
        result = scanner.quick_scan(base_ip)

        if 'error' in result:
            logger.error(f"Quick scan failed: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

        logger.info(f"Quick scan completed. Network: {result.get('network_scanned')}, Hosts: {result.get('total_found')}")
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"Quick scan route error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f"Échec du scan rapide : {str(e)}"
        }), 500

# Health check endpoint for debugging
@network_scan_bp.route('/api/scanner_health', methods=['GET'])
def scanner_health():
    """Check scanner health and dependencies"""
    try:
        health_info = {
            'nmap_available': scanner.check_nmap_installed(),
            'scanner_ready': True,
            'python_version': str(__import__('sys').version_info),
        }
        
        # Test basic network connectivity
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            health_info['internet_connectivity'] = True
        except:
            health_info['internet_connectivity'] = False
        
        return jsonify({
            'success': True,
            'health': health_info
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {'scanner_ready': False}
        }), 500