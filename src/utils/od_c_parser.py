import re

def get_category(index_hex):
    idx = int(index_hex, 16)
    if 0x1000 <= idx <= 0x1FFF:
        return "Communication"
    elif 0x2000 <= idx <= 0x5FFF:
        return "Manufacturer"
    elif 0x6000 <= idx <= 0x9FFF:
        return "Device Profile"
    elif 0xA000 <= idx <= 0xFFFF:
        return "Reserved"
    else:
        return "Unknown"

def parse_od_c(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex para encontrar bloques de variables .o_xxxx_nombre = { ... }
    pattern = re.compile(
        r'\.o_([0-9A-Fa-f]{4})_([a-zA-Z0-9_]+)\s*=\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )

    # Regex para encontrar dataLength = valor
    data_length_pattern = re.compile(r'\.dataLength\s*=\s*([0-9]+)')
    # Regex para encontrar dataType = "tipo"
    data_type_pattern = re.compile(r'\.dataType\s*=\s*"([^"]+)"')

    results = []
    for match in pattern.finditer(content):
        index_hex = match.group(1)
        name = match.group(2)
        block = match.group(3)
        data_length_match = data_length_pattern.search(block)
        data_type_match = data_type_pattern.search(block)
        if data_length_match:
            data_length = int(data_length_match.group(1))
            results.append({
                'index': f"0x{index_hex}",
                'name': name,
                'data_length': data_length,
                'category': get_category(index_hex),
            })
    return results

def parse_application_object(app_obj_value):
    """
    Parsea un application object del formato 0xXXXXYYZZ
    donde XXXX es el index, YY es el subindex, ZZ es la longitud en bits
    """
    if app_obj_value == 0 or app_obj_value == "0x00000000":
        return None
    
    if isinstance(app_obj_value, str):
        value = int(app_obj_value, 16)
    else:
        value = app_obj_value
    
    # Extraer index (bits 31-16), subindex (bits 15-8), longitud (bits 7-0)
    index = (value >> 16) & 0xFFFF
    subindex = (value >> 8) & 0xFF
    bit_length = value & 0xFF
    
    return {
        'index': f"0x{index:04X}",
        'subindex': subindex,
        'bit_length': bit_length,
        'byte_length': bit_length // 8 if bit_length % 8 == 0 else (bit_length // 8) + 1
    }

def parse_pdo_communication_parameters(content):
    """
    Extrae todos los parámetros de comunicación de RPDOs y TPDOs
    """
    # Regex para RPDO Communication Parameters (x1400-x1409)
    rpdo_comm_pattern = re.compile(
        r'\.x(14[0-9A-Fa-f]{2})_RPDOCommunicationParameter\s*=\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    
    # Regex para TPDO Communication Parameters (x1800-x1808)  
    tpdo_comm_pattern = re.compile(
        r'\.x(18[0-9A-Fa-f]{2})_TPDOCommunicationParameter\s*=\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    
    rpdo_comm = {}
    tpdo_comm = {}
    
    # Parsear RPDOs
    for match in rpdo_comm_pattern.finditer(content):
        index_hex = match.group(1).upper()
        block = match.group(2)
        
        # Extraer COB_ID y transmission type
        cob_id_match = re.search(r'\.COB_IDUsedByRPDO\s*=\s*(0x[0-9A-Fa-f]+)', block)
        trans_type_match = re.search(r'\.transmissionType\s*=\s*(0x[0-9A-Fa-f]+)', block)
        
        if cob_id_match and trans_type_match:
            cob_id = int(cob_id_match.group(1), 16)
            trans_type = int(trans_type_match.group(1), 16)
            
            rpdo_comm[index_hex] = {
                'index': f"0x{index_hex}",
                'cob_id': cob_id,
                'cob_id_hex': f"0x{cob_id:08X}",
                'transmission_type': trans_type,
                'enabled': trans_type == 0x01,
                'type': 'RPDO'
            }
    
    # Parsear TPDOs
    for match in tpdo_comm_pattern.finditer(content):
        index_hex = match.group(1).upper()
        block = match.group(2)
        
        # Extraer COB_ID y transmission type
        cob_id_match = re.search(r'\.COB_IDUsedByTPDO\s*=\s*(0x[0-9A-Fa-f]+)', block)
        trans_type_match = re.search(r'\.transmissionType\s*=\s*(0x[0-9A-Fa-f]+)', block)
        
        if cob_id_match and trans_type_match:
            cob_id = int(cob_id_match.group(1), 16)
            trans_type = int(trans_type_match.group(1), 16)
            
            tpdo_comm[index_hex] = {
                'index': f"0x{index_hex}",
                'cob_id': cob_id,
                'cob_id_hex': f"0x{cob_id:08X}",
                'transmission_type': trans_type,
                'enabled': trans_type == 0x01,
                'type': 'TPDO'
            }
    
    return rpdo_comm, tpdo_comm

def parse_pdo_mapping_parameters(content):
    """
    Extrae todos los parámetros de mapeo de RPDOs y TPDOs
    """
    # Regex para RPDO Mapping Parameters (x1600-x1609)
    rpdo_map_pattern = re.compile(
        r'\.x(16[0-9A-Fa-f]{2})_RPDOMappingParameter\s*=\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    
    # Regex para TPDO Mapping Parameters (x1A00-x1A08)
    tpdo_map_pattern = re.compile(
        r'\.x(1A[0-9A-Fa-f]{2})_TPDOMappingParameter\s*=\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    
    rpdo_map = {}
    tpdo_map = {}
    
    # Parsear RPDO Mappings
    for match in rpdo_map_pattern.finditer(content):
        index_hex = match.group(1).upper()
        block = match.group(2)
        
        # Extraer número de objetos mapeados
        num_objects_match = re.search(r'\.numberOfMappedApplicationObjectsInPDO\s*=\s*(0x[0-9A-Fa-f]+)', block)
        if not num_objects_match:
            continue
            
        num_objects = int(num_objects_match.group(1), 16)
        
        # Extraer application objects
        app_objects = []
        for i in range(1, 9):  # applicationObject1 a applicationObject8
            app_obj_match = re.search(f'\.applicationObject{i}\s*=\s*(0x[0-9A-Fa-f]+)', block)
            if app_obj_match:
                app_obj_value = app_obj_match.group(1)
                parsed_obj = parse_application_object(app_obj_value)
                if parsed_obj:
                    app_objects.append(parsed_obj)
        
        rpdo_map[index_hex] = {
            'index': f"0x{index_hex}",
            'num_objects': num_objects,
            'mapped_objects': app_objects,
            'type': 'RPDO_MAP'
        }
    
    # Parsear TPDO Mappings
    for match in tpdo_map_pattern.finditer(content):
        index_hex = match.group(1).upper()
        block = match.group(2)
        
        # Extraer número de objetos mapeados
        num_objects_match = re.search(r'\.numberOfMappedApplicationObjectsInPDO\s*=\s*(0x[0-9A-Fa-f]+)', block)
        if not num_objects_match:
            continue
            
        num_objects = int(num_objects_match.group(1), 16)
        
        # Extraer application objects
        app_objects = []
        for i in range(1, 9):  # applicationObject1 a applicationObject8
            app_obj_match = re.search(f'\.applicationObject{i}\s*=\s*(0x[0-9A-Fa-f]+)', block)
            if app_obj_match:
                app_obj_value = app_obj_match.group(1)
                parsed_obj = parse_application_object(app_obj_value)
                if parsed_obj:
                    app_objects.append(parsed_obj)
        
        tpdo_map[index_hex] = {
            'index': f"0x{index_hex}",
            'num_objects': num_objects,
            'mapped_objects': app_objects,
            'type': 'TPDO_MAP'
        }
    
    return rpdo_map, tpdo_map

def get_pdo_mapping_index(comm_index, pdo_type):
    """
    Convierte el índice de comunicación al índice de mapeo correspondiente
    RPDO: 0x1400 -> 0x1600, 0x1401 -> 0x1601, etc.
    TPDO: 0x1800 -> 0x1A00, 0x1801 -> 0x1A01, etc.
    """
    if pdo_type == 'RPDO':
        # Convertir 0x14XX a 0x16XX
        base_index = int(comm_index, 16)
        mapping_index = 0x1600 + (base_index - 0x1400)
        return f"{mapping_index:04X}"
    elif pdo_type == 'TPDO':
        # Convertir 0x18XX a 0x1AXX
        base_index = int(comm_index, 16)
        mapping_index = 0x1A00 + (base_index - 0x1800)
        return f"{mapping_index:04X}"
    return None

def parse_pdo_mappings(filepath):
    """
    Función principal para extraer todos los mapeos de PDOs con sus variables enlazadas
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parsear parámetros de comunicación y mapeo
    rpdo_comm, tpdo_comm = parse_pdo_communication_parameters(content)
    rpdo_map, tpdo_map = parse_pdo_mapping_parameters(content)
    
    # Combinar comunicación con mapeo
    complete_mappings = {
        'rpdos': [],
        'tpdos': []
    }
    
    # Procesar RPDOs
    for comm_index, comm_data in rpdo_comm.items():
        mapping_index = get_pdo_mapping_index(comm_data['index'], 'RPDO')
        if mapping_index and mapping_index in rpdo_map:
            mapping_data = rpdo_map[mapping_index]
            
            complete_mapping = {
                'communication_index': comm_data['index'],
                'mapping_index': f"0x{mapping_index}",
                'cob_id': comm_data['cob_id'],
                'cob_id_clean': comm_data['cob_id'] & 0x7FF,  # Quitar bits de control
                'enabled': comm_data['enabled'],
                'transmission_type': comm_data['transmission_type'],
                'num_mapped_variables': mapping_data['num_objects'],
                'mapped_variables': mapping_data['mapped_objects'],
                'type': 'RPDO'
            }
            complete_mappings['rpdos'].append(complete_mapping)
    
    # Procesar TPDOs
    for comm_index, comm_data in tpdo_comm.items():
        mapping_index = get_pdo_mapping_index(comm_data['index'], 'TPDO')
        if mapping_index and mapping_index in tpdo_map:
            mapping_data = tpdo_map[mapping_index]
            
            complete_mapping = {
                'communication_index': comm_data['index'],
                'mapping_index': f"0x{mapping_index}",
                'cob_id': comm_data['cob_id'],
                'cob_id_clean': comm_data['cob_id'] & 0x7FF,  # Quitar bits de control
                'enabled': comm_data['enabled'],
                'transmission_type': comm_data['transmission_type'],
                'num_mapped_variables': mapping_data['num_objects'],
                'mapped_variables': mapping_data['mapped_objects'],
                'type': 'TPDO'
            }
            complete_mappings['tpdos'].append(complete_mapping)
    
    return complete_mappings

def debug_pdo_mappings(filepath):
    """
    Función de debugging para mostrar los mapeos extraídos
    """
    print("=== DEBUG: Extrayendo mapeos de PDOs ===")
    mappings = parse_pdo_mappings(filepath)
    
    print(f"\n--- RPDOs encontrados: {len(mappings['rpdos'])} ---")
    for rpdo in mappings['rpdos']:
        print(f"\nRPDO {rpdo['communication_index']} -> {rpdo['mapping_index']}")
        print(f"  COB-ID: 0x{rpdo['cob_id_clean']:03X} (Raw: 0x{rpdo['cob_id']:08X})")
        print(f"  Habilitado: {rpdo['enabled']}")
        print(f"  Variables mapeadas: {rpdo['num_mapped_variables']}")
        
        for i, var in enumerate(rpdo['mapped_variables']):
            print(f"    [{i}] Index: {var['index']}, Sub: {var['subindex']}, Bits: {var['bit_length']}")
    
    print(f"\n--- TPDOs encontrados: {len(mappings['tpdos'])} ---")
    for tpdo in mappings['tpdos']:
        print(f"\nTPDO {tpdo['communication_index']} -> {tpdo['mapping_index']}")
        print(f"  COB-ID: 0x{tpdo['cob_id_clean']:03X} (Raw: 0x{tpdo['cob_id']:08X})")
        print(f"  Habilitado: {tpdo['enabled']}")
        print(f"  Variables mapeadas: {tpdo['num_mapped_variables']}")
        
        for i, var in enumerate(tpdo['mapped_variables']):
            print(f"    [{i}] Index: {var['index']}, Sub: {var['subindex']}, Bits: {var['bit_length']}")
    
    return mappings

if __name__ == "__main__":
    # Para pruebas manuales
    print("=== Parsing OD variables ===")
    regs = parse_od_c("OD.c")
    for r in regs:
        print(r)
    
    print("\n" + "="*50)
    print("=== Parsing PDO mappings ===")
    debug_pdo_mappings("OD.c")
