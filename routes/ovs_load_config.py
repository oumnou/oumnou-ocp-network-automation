import os
import yaml
from flask import Blueprint, request, jsonify
from services.ovs_configurator import apply_configuration_from_yaml

load_config_bp = Blueprint('load_config_bp', __name__)
BACKUP_DIR = 'backup'

@load_config_bp.route('/api/load_config', methods=['POST'])
def load_config():
    try:
        data = request.get_json()
        backup_file = data.get('backup_file')
        switch_name = data.get('switch_name')  # This is the IP or hostname
        password = data.get('password')

        if not all([backup_file, switch_name, password]):
            return jsonify({'success': False, 'error': 'Champs manquants'}), 400

        backup_path = os.path.join(BACKUP_DIR, backup_file)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Fichier non trouvé'}), 404

        # Load YAML file here, get dict
        with open(backup_path, 'r') as f:
            config_data = yaml.safe_load(f)
            print("Type of config_data:", type(config_data))  # should be <class 'dict'>
            print("config_data keys:", config_data.keys())

        # Pass parsed dict to apply_configuration_from_yaml
        result = apply_configuration_from_yaml(config_data, switch_name, password)

        return jsonify({'success': True, 'results': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
