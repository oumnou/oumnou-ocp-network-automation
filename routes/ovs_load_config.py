import os
import yaml
from flask import Blueprint, request, jsonify
from services.ovs_configurator import apply_configuration_from_yaml

load_config_bp = Blueprint('load_config_bp', __name__)
BACKUP_DIR = 'backup'

@load_config_bp.route('/api/load_config', methods=['POST'])
def load_config():
    try:
        # Ensure we get JSON data
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type doit être application/json'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Aucune donnée JSON reçue'}), 400
        
        backup_file = data.get('backup_file')
        switch_ip = data.get('switch_name')  # This should be the IP address, not bridge name
        password = data.get('password')

        if not all([backup_file, switch_ip, password]):
            missing_fields = []
            if not backup_file:
                missing_fields.append('backup_file')
            if not switch_ip:
                missing_fields.append('switch_ip')
            if not password:
                missing_fields.append('password')
            
            return jsonify({
                'success': False, 
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            }), 400

        backup_path = os.path.join(BACKUP_DIR, backup_file)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': f'Fichier non trouvé: {backup_file}'}), 404

        # Load YAML file here, get dict
        try:
            with open(backup_path, 'r') as f:
                config_data = yaml.safe_load(f)
                print("Type of config_data:", type(config_data))  # should be <class 'dict'>
                if config_data:
                    print("config_data keys:", config_data.keys())
        except yaml.YAMLError as e:
            return jsonify({'success': False, 'error': f'Erreur lors du parsing YAML: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'Erreur lors de la lecture du fichier: {str(e)}'}), 400

        if not config_data:
            return jsonify({'success': False, 'error': 'Le fichier de configuration est vide ou invalide'}), 400

        # Pass parsed dict to apply_configuration_from_yaml
        result = apply_configuration_from_yaml(config_data, switch_ip, password)

        return jsonify({'success': True, 'results': result})

    except Exception as e:
        print(f"Erreur dans load_config: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Erreur serveur: {str(e)}'}), 500