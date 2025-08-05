from .ssh_utils import run_ovs_command, clean_ovs_output

def generate_backup_commands(bridge_data, port_data, interface_data):
    commands = []
    
    # Parse port blocks into dict uuid -> name
    port_blocks = []
    current_block = []
    for line in port_data.splitlines():
        if line.strip() == "":
            if current_block:
                port_blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        port_blocks.append(current_block)
    
    port_uuid_to_name = {}
    for block in port_blocks:
        port_uuid = None
        port_name = None
        for line in block:
            line = line.strip()
            if line.startswith("_uuid"):
                port_uuid = line.split(":", 1)[1].strip()
            elif line.startswith("name"):
                port_name = line.split(":", 1)[1].strip().strip('"')
        if port_uuid:
            port_uuid_to_name[port_uuid] = port_name  # port_name can be None

    # Parse interface blocks into dict uuid -> name
    iface_blocks = []
    current_block = []
    for line in interface_data.splitlines():
        if line.strip() == "":
            if current_block:
                iface_blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        iface_blocks.append(current_block)
    
    iface_uuid_to_name = {}
    for block in iface_blocks:
        iface_uuid = None
        iface_name = None
        for line in block:
            line = line.strip()
            if line.startswith("_uuid"):
                iface_uuid = line.split(":", 1)[1].strip()
            elif line.startswith("name"):
                iface_name = line.split(":", 1)[1].strip().strip('"')
        if iface_uuid and iface_name:
            iface_uuid_to_name[iface_uuid] = iface_name

    # Parse bridges and their port UUIDs
    bridges = {}
    current_bridge = None
    for line in bridge_data.splitlines():
        line = line.strip()
        if line.startswith("name"):
            current_bridge = line.split(":", 1)[1].strip().strip('"')
            bridges[current_bridge] = []
        elif line.startswith("ports") and current_bridge:
            ports_str = line.split(":", 1)[1].strip().strip("[]")
            ports = [p.strip() for p in ports_str.split(",") if p.strip()]
            bridges[current_bridge].extend(ports)

    # Build commands for bridges and ports
    for br in bridges:
        commands.append(f"ovs-vsctl add-br {br}")
        for port_uuid in bridges[br]:
            port_name = port_uuid_to_name.get(port_uuid)
            if port_name:
                commands.append(f"ovs-vsctl add-port {br} {port_name}")
            else:
                iface_name = iface_uuid_to_name.get(port_uuid)
                if iface_name:
                    commands.append(f"ovs-vsctl add-port {br} {iface_name}")
                else:
                    commands.append(f"ovs-vsctl add-port {br} {port_uuid}")

    # Add interface types and tags
    for block in iface_blocks:
        iface_name = None
        iface_type = None
        iface_tag = None
        for line in block:
            line = line.strip()
            if line.startswith("name"):
                iface_name = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("type"):
                iface_type = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("tag"):
                iface_tag = line.split(":", 1)[1].strip()
        if iface_name:
            if iface_type:
                commands.append(f"ovs-vsctl set Interface {iface_name} type={iface_type}")
            if iface_tag:
                commands.append(f"ovs-vsctl set port {iface_name} tag={iface_tag}")

    return "\n".join(commands)
