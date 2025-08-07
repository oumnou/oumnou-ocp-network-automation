# routes/network_scan.py

from flask import Blueprint, request, jsonify
from services.network_scanner import NetworkScanner
import re

network_scan_bp = Blueprint('network_scan', __name__)
scanner = NetworkScanner()

@network_scan_bp.route('/api/scan_network', methods=['POST'])
def scan_network():
    """Scan network range for potential switches"""
    try:
        data = request.json or {}
        network_range = data.get('network_range')

        if not network_range:
            return jsonify({
                'success': False,
                'error': 'La plage réseau est requise (ex: 192.168.1.0/24)'
            }), 400

        # Validate network range format (e.g., 192.168.1.0/24)
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$', network_range):
            return jsonify({
                'success': False,
                'error': 'Format de plage réseau invalide. Format attendu : 192.168.1.0/24'
            }), 400

        # Perform network scan
        result = scanner.scan_network(network_range)

        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

        return jsonify({
            'success': True,
            'hosts': result['hosts'],
            'total_found': len(result['hosts']),
            'switch_candidates': len([
                h for h in result['hosts'] if h.get('is_switch_candidate')
            ])
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Échec du scan : {str(e)}"
        }), 500

@network_scan_bp.route('/api/test_switch', methods=['POST'])
def test_switch():
    """Test SSH connectivity and check if it's an OVS switch"""
    try:
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

        # Run the connectivity test
        result = scanner.test_switch_connectivity(ip, username, password)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Échec du test : {str(e)}"
        }), 500

@network_scan_bp.route('/api/quick_scan', methods=['POST'])
def quick_scan():
    """Quick scan based on provided base IP (e.g., 192.168.1.1)"""
    try:
        data = request.json or {}
        base_ip = data.get('base_ip', '192.168.1.1')

        # Extract subnet from base IP
        ip_parts = base_ip.split('.')
        if len(ip_parts) != 4:
            return jsonify({
                'success': False,
                'error': 'Format IP invalide'
            }), 400

        network_range = f"{'.'.join(ip_parts[:3])}.0/24"

        # Perform the scan
        result = scanner.scan_network(network_range)

        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

        return jsonify({
            'success': True,
            'network_scanned': network_range,
            'hosts': result['hosts'],
            'total_found': len(result['hosts']),
            'switch_candidates': len([
                h for h in result['hosts'] if h.get('is_switch_candidate')
            ])
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Échec du scan rapide : {str(e)}"
        }), 500
