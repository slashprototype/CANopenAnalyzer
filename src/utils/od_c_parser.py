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

if __name__ == "__main__":
    # Para pruebas manuales
    regs = parse_od_c("OD.c")
    for r in regs:
        print(r)
    parse_od_c("OD.c")
