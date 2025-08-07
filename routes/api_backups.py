# routes/api_backups.py

from flask import Blueprint, jsonify, request
import os
from services.ssh_utils import run_ovs_command, clean_ovs_output

backup_api = Blueprint('backup_api', __name__)

BACKUP_FOLDER = 'backup'

@backup_api.route('/api/list_backups')
def list_backups():
    try:
        files = []
        if os.path.exists(BACKUP_FOLDER):
            files = [f for f in os.listdir(BACKUP_FOLDER) if f.endswith('.yaml')]
        return jsonify({'files': files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@backup_api.route('/api/list_bridges', methods=['POST'])
def list_bridges():
    """Get list of available bridges on the switch"""
    try:
        data = request.json or {}
        password = data.get("password")
        
        if not password:
            return jsonify({"success": False, "error": "Password is required."}), 400
        
        # Get list of bridges
        raw_output, err = run_ovs_command("ovs-vsctl list-br", password=password)
        
        if err:
            return jsonify({
                "success": False, 
                "error": f"Error getting bridge list: {err}"
            }), 500
        
        bridges = []
        cleaned_output = clean_ovs_output(raw_output)
        if cleaned_output.strip():
            bridges = [b.strip() for b in cleaned_output.splitlines() if b.strip()]
        
        return jsonify({
            "success": True,
            "bridges": bridges
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500