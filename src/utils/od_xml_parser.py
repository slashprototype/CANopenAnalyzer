import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import re
from .od_c_parser import ODCParser

class ODXMLParser:
    def __init__(self, xml_file_path: str, od_c_file_path: Optional[str] = None):
        self.xml_file_path = xml_file_path
        self.od_c_file_path = od_c_file_path
        self.tree = None
        self.root = None
        self.objects = {}
        self.communication_params = {}
        self.manufacturer_params = {}
        self.device_profile_params = {}
        self.pdo_mappings = {}
        self.od_c_parser = None
        
        # Initialize OD.c parser if file is provided
        if od_c_file_path:
            try:
                self.od_c_parser = ODCParser(od_c_file_path)
            except Exception as e:
                print(f"Warning: Could not parse OD.c file: {e}")
        
        self.load_xml()
        
    def load_xml(self):
        """Load and parse the XML file"""
        try:
            self.tree = ET.parse(self.xml_file_path)
            self.root = self.tree.getroot()
            self.parse_objects()
        except Exception as e:
            raise Exception(f"Error loading XML file: {e}")
    
    def parse_objects(self):
        """Parse all CANopen objects from XML"""
        canopen_list = self.root.find('CANopenObjectList')
        if canopen_list is None:
            raise Exception("No CANopenObjectList found in XML")
            
        for obj in canopen_list.findall('CANopenObject'):
            index = obj.get('index')
            if index:
                parsed_obj = self._parse_object(obj)
                self.objects[index] = parsed_obj
                self._categorize_object(index, parsed_obj)
    
    def _parse_object(self, obj_element) -> Dict[str, Any]:
        """Parse individual CANopen object"""
        # Get description text safely
        desc_element = obj_element.find('description')
        description = ''
        if desc_element is not None and desc_element.text is not None:
            description = desc_element.text
        
        obj_data = {
            'index': obj_element.get('index'),
            'name': obj_element.get('name', ''),
            'objectType': obj_element.get('objectType', ''),
            'memoryType': obj_element.get('memoryType', ''),
            'dataType': obj_element.get('dataType', ''),
            'accessType': obj_element.get('accessType', ''),
            'PDOmapping': obj_element.get('PDOmapping', ''),
            'defaultValue': obj_element.get('defaultValue', ''),
            'highValue': obj_element.get('highValue', ''),
            'lowValue': obj_element.get('lowValue', ''),
            'subNumber': obj_element.get('subNumber', ''),
            'disabled': obj_element.get('disabled') == 'true',
            'TPDOdetectCOS': obj_element.get('TPDOdetectCOS') == 'true',
            'description': description,
            'subObjects': []
        }
        
        # Parse sub-objects if they exist
        for sub_obj in obj_element.findall('CANopenSubObject'):
            # Get sub-object description safely
            sub_desc_element = sub_obj.find('description')
            sub_description = ''
            if sub_desc_element is not None and sub_desc_element.text is not None:
                sub_description = sub_desc_element.text
                
            sub_data = {
                'subIndex': sub_obj.get('subIndex', ''),
                'name': sub_obj.get('name', ''),
                'objectType': sub_obj.get('objectType', ''),
                'dataType': sub_obj.get('dataType', ''),
                'accessType': sub_obj.get('accessType', ''),
                'PDOmapping': sub_obj.get('PDOmapping', ''),
                'defaultValue': sub_obj.get('defaultValue', ''),
                'highValue': sub_obj.get('highValue', ''),
                'lowValue': sub_obj.get('lowValue', ''),
                'TPDOdetectCOS': sub_obj.get('TPDOdetectCOS') == 'true',
                'description': sub_description
            }
            obj_data['subObjects'].append(sub_data)
            
        return obj_data
    
    def _categorize_object(self, index: str, obj_data: Dict[str, Any]):
        """Categorize objects by type"""
        index_int = int(index, 16)
        
        # Communication parameters (0x1000-0x1FFF)
        if 0x1000 <= index_int <= 0x1FFF:
            self.communication_params[index] = obj_data
            
        # Manufacturer parameters (0x2000-0x5FFF)
        elif 0x2000 <= index_int <= 0x5FFF:
            self.manufacturer_params[index] = obj_data
            
        # Device profile specific (0x6000-0x9FFF)
        elif 0x6000 <= index_int <= 0x9FFF:
            self.device_profile_params[index] = obj_data
    
    def extract_pdo_mappings(self):
        """Extract PDO mapping information, grouping mapped parameters by index"""
        rpdo_mappings = {}
        tpdo_mappings = {}

        # Extract RPDO communication parameters (0x1400-0x15FF)
        rpdo_comm_params = {}
        for index, obj in self.communication_params.items():
            index_int = int(index, 16)
            if 0x1400 <= index_int <= 0x15FF:
                rpdo_comm_params[index] = obj

        # Extract TPDO communication parameters (0x1800-0x19FF)
        tpdo_comm_params = {}
        for index, obj in self.communication_params.items():
            index_int = int(index, 16)
            if 0x1800 <= index_int <= 0x19FF:
                tpdo_comm_params[index] = obj

        # Helper to group mapped objects by index
        def group_by_index(mapped_objects):
            if not mapped_objects:  # Handle None or empty list case
                return []
                
            grouped = {}
            for mapped in mapped_objects:
                if not mapped or 'index' not in mapped:  # Skip if mapped is None or doesn't have index
                    continue
                idx = mapped['index']
                if idx not in grouped:
                    grouped[idx] = {
                        'index': idx,
                        'name': mapped.get('name', 'Unknown'),
                        'sub_mappings': []
                    }
                grouped[idx]['sub_mappings'].append(mapped)
            return list(grouped.values())

        # Extract RPDO mapping parameters (0x1600-0x17FF)
        for index, obj in self.communication_params.items():
            try:
                index_int = int(index, 16)
                if 0x1600 <= index_int <= 0x17FF:
                    pdo_num = index_int - 0x1600
                    mapping = self._parse_pdo_mapping(obj, rpdo_comm_params.get(f"{0x1400 + pdo_num:04X}"))
                    if mapping and 'mapped_objects' in mapping:  # Check if mapping is valid
                        # Agrupa los mapped_objects por index
                        mapping['mapped_parameters'] = group_by_index(mapping.get('mapped_objects', []))
                        rpdo_mappings[f"RPDO{pdo_num + 1}"] = mapping
            except Exception as e:
                print(f"Error extracting RPDO mapping for {index}: {e}")

        # Extract TPDO mapping parameters (0x1A00-0x1BFF)
        for index, obj in self.communication_params.items():
            try:
                index_int = int(index, 16)
                if 0x1A00 <= index_int <= 0x1BFF:
                    pdo_num = index_int - 0x1A00
                    mapping = self._parse_pdo_mapping(obj, tpdo_comm_params.get(f"{0x1800 + pdo_num:04X}"))
                    if mapping and 'mapped_objects' in mapping:  # Check if mapping is valid
                        # Agrupa los mapped_objects por index
                        mapping['mapped_parameters'] = group_by_index(mapping.get('mapped_objects', []))
                        tpdo_mappings[f"TPDO{pdo_num + 1}"] = mapping
            except Exception as e:
                print(f"Error extracting TPDO mapping for {index}: {e}")

        self.pdo_mappings = {
            'RPDO': rpdo_mappings,
            'TPDO': tpdo_mappings
        }

        return self.pdo_mappings
    
    def _parse_pdo_mapping(self, mapping_obj: Dict[str, Any], comm_obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse individual PDO mapping"""
        mapping_data = {
            'mapping_index': mapping_obj['index'],
            'name': mapping_obj['name'],
            'cob_id': None,
            'transmission_type': None,
            'event_timer': None,
            'mapped_objects': []
        }
        
        # Extract communication parameters
        if comm_obj:
            for sub_obj in comm_obj['subObjects']:
                if 'COB-ID' in sub_obj['name']:
                    mapping_data['cob_id'] = sub_obj['defaultValue']
                elif 'Transmission type' in sub_obj['name']:
                    mapping_data['transmission_type'] = sub_obj['defaultValue']
                elif 'Event timer' in sub_obj['name']:
                    mapping_data['event_timer'] = sub_obj['defaultValue']
        
        # Extract mapped objects
        for sub_obj in mapping_obj['subObjects']:
            if sub_obj['subIndex'] != '00' and sub_obj['defaultValue'] and sub_obj['defaultValue'] != '0x00000000':
                mapped_obj = self._parse_mapped_object(sub_obj['defaultValue'])
                if mapped_obj:
                    mapping_data['mapped_objects'].append(mapped_obj)
        
        return mapping_data
    
    def _get_data_type_size(self, data_type: str, index: str = None, sub_index: str = None) -> int:
        """Get the size in bits for a given CANopen data type, with OD.c override"""

        # Always use uppercase and 4-digit index
        od_index = index.upper() if index else None
        if od_index and len(od_index) < 4:
            od_index = od_index.zfill(4)

        # Try OD.c with sub-index first (for records/arrays)
        if self.od_c_parser and od_index:
            if sub_index:
                od_c_size_bits = self.od_c_parser.get_data_length_bits(od_index, sub_index)
                if od_c_size_bits is not None:
                    print(f"✓ Using OD.c size for {od_index}:{sub_index}: {od_c_size_bits} bits")
                    return od_c_size_bits
            od_c_size_bits = self.od_c_parser.get_data_length_bits(od_index)
            if od_c_size_bits is not None:
                print(f"✓ Using OD.c size for {od_index}: {od_c_size_bits} bits")
                return od_c_size_bits
        
        # Handle None or empty data_type
        if not data_type:
            print(f"Warning: Empty data type for index {index}. Defaulting to 8 bits.")
            return 8
        
        # Fallback to data type mapping
        # CANopen data types (hex values from CiA standard)
        data_type_sizes = {
            'BOOLEAN': 1,
            'INTEGER8': 8, '0x02': 8,
            'UNSIGNED8': 8, '0x05': 8,
            'INTEGER16': 16, '0x03': 16,
            'UNSIGNED16': 16, '0x06': 16,
            'INTEGER32': 32, '0x04': 32,
            'UNSIGNED32': 32, '0x07': 32,
            'REAL32': 32, '0x08': 32,
            'INTEGER64': 64, 
            'UNSIGNED64': 64, '0x1B': 64,
            'REAL64': 64, '0x11': 64,
            'VISIBLE_STRING': 8, '0x09': 8,
            'OCTET_STRING': 8, '0x0A': 8,
            'UNICODE_STRING': 16, '0x0B': 16,
            'DOMAIN': 8, '0x0F': 8,
            'TIME_OF_DAY': 48, '0x0C': 48,
            'TIME_DIFFERENCE': 48, '0x0D': 48
        }
        
        try:
            clean_type = data_type.strip().upper()
            
            # Direct lookup for hex values (0xNN format)
            if clean_type.startswith('0X'):
                if clean_type in data_type_sizes:
                    size = data_type_sizes[clean_type]
                    print(f"✓ Found exact match for data type {clean_type}: {size} bits for index {index}")
                    return size
        
            # String type name lookup
            for type_name, size in data_type_sizes.items():
                if type_name in clean_type:
                    print(f"✓ Using size for {type_name} ({size} bits) for index {index}")
                    return size
            
            print(f"Warning: Unknown data type '{data_type}' for index {index}. Defaulting to 8 bits.")
        except (AttributeError, TypeError) as e:
            print(f"Error processing data type: {e} for index {index}. Defaulting to 8 bits.")
            
        return 8
    
    def _parse_mapped_object(self, mapping_value: str) -> Optional[Dict[str, Any]]:
        """Parse mapped object from mapping value (0xIIIISSLL format)"""
        if not mapping_value or mapping_value == '0x00000000':
            return None
            
        try:
            value = int(mapping_value, 16)
            index = f"{(value >> 16) & 0xFFFF:04X}".upper()
            sub_index = f"{(value >> 8) & 0xFF:02X}".upper()
            length_from_mapping = value & 0xFF
            
            actual_data_type = None
            actual_length_bits = None
            od_c_length_bits = None
            obj_name = "Unknown"
            
            # Try OD.c with sub-index first
            if self.od_c_parser:
                od_c_length_bits = self.od_c_parser.get_data_length_bits(index, sub_index)
                if od_c_length_bits is None:
                    od_c_length_bits = self.od_c_parser.get_data_length_bits(index)
                if od_c_length_bits:
                    print(f"✓ Using OD.c definitive size for {index}:{sub_index} or {index}: {od_c_length_bits} bits")
            
            if index in self.objects:
                obj = self.objects[index]
                obj_name = obj['name']
                
                # If it's a single object (not array or record)
                if obj['objectType'] in ['VAR', '7'] and sub_index == '00':
                    actual_data_type = obj['dataType']
                    if actual_data_type:
                        actual_length_bits = self._get_data_type_size(actual_data_type, index)
                
                # If it has sub-objects, try to find specific sub-object
                elif obj['subObjects']:
                    for sub_obj in obj['subObjects']:
                        sub_obj_index = sub_obj.get('subIndex')
                        if sub_obj_index and sub_obj_index.upper().zfill(2) == sub_index:
                            obj_name = sub_obj['name']
                            actual_data_type = sub_obj['dataType']
                            if actual_data_type:
                                actual_length_bits = self._get_data_type_size(actual_data_type, index, sub_index)
                            break
            
            # PRIORITY ORDER: OD.c (definitive) > mapping > XML data type
            if od_c_length_bits:
                length_bits = od_c_length_bits
            else:
                length_bits = length_from_mapping if length_from_mapping else (actual_length_bits or 8)
            
            # Check for discrepancies only if we have OD.c data
            has_discrepancy = False
            discrepancy_info = {}
            
            if od_c_length_bits and length_from_mapping and od_c_length_bits != length_from_mapping:
                has_discrepancy = True
                discrepancy_info['od_c_vs_mapping'] = f"OD.c: {od_c_length_bits} bits (USED), Mapping: {length_from_mapping} bits"
            
            return {
                'index': index,
                'sub_index': sub_index,
                'length_bits': length_bits,
                'length_bytes': max(1, length_bits // 8),
                'name': obj_name,
                'mapping_value': mapping_value,
                'data_type': actual_data_type,
                'mapping_length': length_from_mapping,
                'actual_length': actual_length_bits,
                'od_c_length': od_c_length_bits,
                'has_size_discrepancy': has_discrepancy,
                'discrepancy_info': discrepancy_info,
                'definitive_size_bits': length_bits,
                'definitive_size_bytes': max(1, length_bits // 8)
            }
        except (ValueError, TypeError) as e:
            print(f"Error parsing mapped object {mapping_value}: {e}")
            return None

    def get_device_info(self) -> Dict[str, Any]:
        """Extract device information from XML"""
        device_info = {}
        
        # Extract from 'other' section if it exists
        other_section = self.root.find('other')
        if other_section is not None:
            # File information
            file_info = other_section.find('file')
            if file_info is not None:
                device_info['file_info'] = dict(file_info.attrib)
            
            # Device identity
            identity = other_section.find('DeviceIdentity')
            if identity is not None:
                device_info['device_identity'] = {}
                for child in identity:
                    if child.text is not None:
                        device_info['device_identity'][child.tag] = child.text
            
            # Capabilities
            capabilities = other_section.find('capabilities')
            if capabilities is not None:
                device_info['capabilities'] = {}
                char_list = capabilities.find('characteristicsList')
                if char_list is not None:
                    for char in char_list.findall('characteristic'):
                        name_elem = char.find('characteristicName/label')
                        content_elem = char.find('characteristicContent/label')
                        if name_elem is not None and content_elem is not None and name_elem.text is not None and content_elem.text is not None:
                            device_info['capabilities'][name_elem.text] = content_elem.text
            
            # Baud rates
            baud_rate = other_section.find('baudRate')
            if baud_rate is not None:
                device_info['supported_baud_rates'] = []
                for rate in baud_rate.findall('supportedBaudRate'):
                    rate_value = rate.get('value')
                    if rate_value:
                        device_info['supported_baud_rates'].append(rate_value)
        
        return device_info
    
    def get_enhanced_object_info(self, index: str) -> Optional[Dict[str, Any]]:
        """Get enhanced object information combining XML and OD.c data"""
        if index not in self.objects:
            return None
        
        obj = self.objects[index]
        enhanced_info = obj.copy()
        
        # Add OD.c information if available
        if self.od_c_parser:
            od_c_length = self.od_c_parser.get_data_length(index)
            
            enhanced_info['od_c_data_length_bytes'] = od_c_length
            enhanced_info['od_c_data_length_bits'] = od_c_length * 8 if od_c_length else None
        
        return enhanced_info
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of parsed OD"""
        summary = {
            'total_objects': len(self.objects),
            'communication_params': len(self.communication_params),
            'manufacturer_params': len(self.manufacturer_params),
            'device_profile_params': len(self.device_profile_params),
            'xml_file': self.xml_file_path,
            'device_info': self.get_device_info() or {}  # Ensure device_info is never None
        }
        
        # Add OD.c summary if available
        if self.od_c_parser:
            summary['od_c_file'] = self.od_c_file_path
            od_c_summary = self.od_c_parser.get_summary()
            summary['od_c_summary'] = od_c_summary if od_c_summary is not None else {}
        
        return summary