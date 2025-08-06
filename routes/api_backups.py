# routes/api_backups.py

from flask import Blueprint, jsonify
import os

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
