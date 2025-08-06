import yaml
from services.ssh_utils import run_ovs_command

def apply_configuration_from_yaml(config, switch_host, ssh_password):
    """
    Applique la configuration OVS depuis un dict 'config' sur le switch distant.

    Args:
        config (dict): dictionnaire de configuration YAML déjà chargé.
        switch_host (str): hostname ou IP du switch distant.
        ssh_password (str): mot de passe SSH.

    Returns:
        list: liste des tuples (commande, sortie, erreur).
    """
    results = []

    # Apply bridges
    for bridge in config.get('bridges', []):
        bridge_name = bridge.get('name')
        if bridge_name:
            cmd = f"ovs-vsctl add-br {bridge_name}"
            out, err = run_ovs_command(cmd, hostname=switch_host, password=ssh_password)
            results.append((cmd, out, err))

            for port in bridge.get('ports', []):
                port_name = port.get('name')
                if port_name:
                    cmd_port = f"ovs-vsctl add-port {bridge_name} {port_name}"
                    out, err = run_ovs_command(cmd_port, hostname=switch_host, password=ssh_password)
                    results.append((cmd_port, out, err))

    return results
