from typing import Dict, Any, Optional

class XMLRegister:
    def __init__(self, index: str, obj_data: Dict[str, Any], sub_index: Optional[str] = None, od_c_length: Optional[int] = None):
        self.index = index.upper() if index else "0000"
        self.sub_index = sub_index.upper() if sub_index else None
        self.name = obj_data.get('name', 'Unknown')
        self.object_type = obj_data.get('objectType', 'VAR')
        self.data_type = obj_data.get('dataType', '0x00')
        self.access_type = obj_data.get('accessType', 'ro')
        self.pdo_mapping = obj_data.get('PDOmapping', 'no')
        self.default_value = obj_data.get('defaultValue', '')
        self.high_value = obj_data.get('highValue', '')
        self.low_value = obj_data.get('lowValue', '')
        self.memory_type = obj_data.get('memoryType', 'RAM')
        self.disabled = obj_data.get('disabled', False)
        self.description = obj_data.get('description', '')
        self.current_value = self.default_value
        
        # Store OD.c length if provided
        self.od_c_length_bytes = od_c_length
        self.od_c_length_bits = od_c_length * 8 if od_c_length else None

        # Calculate size based on OD.c data first, then data type
        if self.od_c_length_bits:
            self.size = self.od_c_length_bits
        else:
            self.size = self._calculate_size_from_data_type(self.data_type)
        
        # For PDO mapping
        self.cob_id = None
        self.position = 0
        self.pdo_type = None
    
    def _calculate_size_from_data_type(self, data_type: str) -> int:
        """Calculate size in bits from CANopen data type, with OD.c override"""
        
        # If we have OD.c length information, use it as priority
        if self.od_c_length_bits:
            return self.od_c_length_bits
        
        if not data_type:
            return 32
            
        data_type_sizes = {
            '0x01': 1,   # BOOLEAN
            '0x02': 8,   # INTEGER8
            '0x03': 16,  # INTEGER16
            '0x04': 32,  # INTEGER32
            '0x05': 8,   # UNSIGNED8
            '0x06': 16,  # UNSIGNED16
            '0x07': 32,  # UNSIGNED32
            '0x08': 32,  # REAL32
            '0x09': 0,   # VISIBLE_STRING (variable)
            '0x0A': 0,   # OCTET_STRING (variable)
            '0x0B': 0,   # UNICODE_STRING (variable)
            '0x0C': 0,   # TIME_OF_DAY (variable)
            '0x0D': 0,   # TIME_DIFFERENCE (variable)
            '0x0E': 0,   # DOMAIN (variable)
            '0x0F': 32,  # INTEGER24
            '0x10': 64,  # REAL64
            '0x11': 40,  # INTEGER40
            '0x12': 48,  # INTEGER48
            '0x13': 56,  # INTEGER56
            '0x14': 64,  # INTEGER64
            '0x15': 24,  # UNSIGNED24
            '0x16': 40,  # UNSIGNED40
            '0x17': 48,  # UNSIGNED48
            '0x18': 56,  # UNSIGNED56
            '0x19': 64,  # UNSIGNED64
        }
        return data_type_sizes.get(data_type, 32)  # Default to 32 bits
    
    def get_full_index(self) -> str:
        """Get full index including sub-index if applicable"""
        if self.sub_index:
            return f"{self.index}:{self.sub_index}"
        return self.index
    
    def is_readable(self) -> bool:
        """Check if register is readable"""
        return 'r' in self.access_type
    
    def is_writable(self) -> bool:
        """Check if register is writable"""
        return 'w' in self.access_type
    
    def is_pdo_mappable(self) -> bool:
        """Check if register can be mapped to PDO"""
        return self.pdo_mapping in ['RPDO', 'TPDO', 'optional']
    
    def get_register_dictionary(self) -> Dict[str, Any]:
        """Get register data as dictionary for compatibility"""
        return {
            self.get_full_index(): {
                'index': self.index,
                'sub_index': self.sub_index,
                'name': self.name,
                'type': self.pdo_type or 'OD',
                'object_type': self.object_type,
                'data_type': self.data_type,
                'access_type': self.access_type,
                'pdo_mapping': self.pdo_mapping,
                'size': self.size,
                'size_bytes': self.size // 8 if self.size >= 8 else 1,
                'od_c_size_bytes': self.od_c_length_bytes,
                'od_c_size_bits': self.od_c_length_bits,
                'cob_id': self.cob_id,
                'position': self.position,
                'value': self.current_value,
                'default_value': self.default_value,
                'memory_type': self.memory_type,
                'disabled': self.disabled,
                'description': self.description
            }
        }
    
    def update_value(self, new_value: Any):
        """Update current value"""
        self.current_value = new_value
    
    def __str__(self) -> str:
        return f"XMLRegister({self.get_full_index()}: {self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()
