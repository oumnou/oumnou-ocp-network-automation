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
    
    try:
        # Apply bridges
        for bridge in config.get('bridges', []):
            bridge_name = bridge.get('name')
            if bridge_name:
                # First, try to add the bridge (ignore if it already exists)
                cmd = f"ovs-vsctl --may-exist add-br {bridge_name}"
                out, err = run_ovs_command(cmd, hostname=switch_host, password=ssh_password)
                results.append((cmd, out, err))

                # Then add ports to the bridge
                for port in bridge.get('ports', []):
                    port_name = port.get('name')
                    port_type = port.get('type', '')
                    
                    if port_name:
                        # Add port to bridge (ignore if it already exists)
                        cmd_port = f"ovs-vsctl --may-exist add-port {bridge_name} {port_name}"
                        out, err = run_ovs_command(cmd_port, hostname=switch_host, password=ssh_password)
                        results.append((cmd_port, out, err))
                        
                        # Set interface type if specified and not empty
                        if port_type and port_type.strip() and port_type != '""' and port_type != "''":
                            cmd_type = f"ovs-vsctl set Interface {port_name} type={port_type}"
                            out, err = run_ovs_command(cmd_type, hostname=switch_host, password=ssh_password)
                            results.append((cmd_type, out, err))

        # Apply interfaces configuration if available
        for interface in config.get('interfaces', []):
            iface_name = interface.get('name')
            iface_type = interface.get('type', '')
            
            if iface_name and iface_type and iface_type.strip() and iface_type != '""' and iface_type != "''":
                cmd_iface = f"ovs-vsctl set Interface {iface_name} type={iface_type}"
                out, err = run_ovs_command(cmd_iface, hostname=switch_host, password=ssh_password)
                results.append((cmd_iface, out, err))

    except Exception as e:
        results.append((f"ERROR", f"Exception occurred: {str(e)}", str(e)))

    return results