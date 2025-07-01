import time
from typing import Dict, List, Tuple
from interfaces import CANMessage

class DataCollector:
    def __init__(self, logger, interface_manager):
        self.logger = logger
        self.interface_manager = interface_manager
        
        # Data storage
        self.variable_history = {}  # {var_index: [(timestamp, value), ...]}
        self.max_history_points = 1000
        self.is_monitoring = False
        
        # PDO mappings
        self.cob_id_to_pdo = {}
        self.pdo_variables = {}
        
    def build_cob_id_mapping(self, pdo_mappings):
        """Build mapping from COB-ID to PDO information for quick lookup"""
        self.cob_id_to_pdo = {}
        
        self.logger.info(f"Building COB-ID mapping from PDO mappings: {type(pdo_mappings)}")
        
        if isinstance(pdo_mappings, dict):
            # Process RPDOs and TPDOs
            rpdos = pdo_mappings.get('rpdos', [])
            tpdos = pdo_mappings.get('tpdos', [])
            
            self.logger.info(f"Found {len(rpdos)} RPDOs and {len(tpdos)} TPDOs")
            
            for rpdo in rpdos:
                if rpdo.get('enabled') and rpdo.get('mapped_variables'):
                    cob_id = rpdo.get('cob_id_clean')
                    if cob_id is not None:
                        self.cob_id_to_pdo[cob_id] = {
                            'type': 'RPDO',
                            'pdo_info': rpdo
                        }
                        self.logger.debug(f"Added RPDO mapping: COB-ID 0x{cob_id:03X} with {len(rpdo['mapped_variables'])} variables")
            
            for tpdo in tpdos:
                if tpdo.get('enabled') and tpdo.get('mapped_variables'):
                    cob_id = tpdo.get('cob_id_clean')
                    if cob_id is not None:
                        self.cob_id_to_pdo[cob_id] = {
                            'type': 'TPDO',
                            'pdo_info': tpdo
                        }
                        self.logger.debug(f"Added TPDO mapping: COB-ID 0x{cob_id:03X} with {len(tpdo['mapped_variables'])} variables")
        
        else:
            self.logger.warning(f"Unexpected PDO mappings format: {type(pdo_mappings)}")
        
        self.logger.info(f"Built COB-ID mapping for {len(self.cob_id_to_pdo)} enabled PDOs")
        
        # Log the final mapping for debugging
        for cob_id, info in self.cob_id_to_pdo.items():
            var_count = len(info['pdo_info'].get('mapped_variables', []))
            self.logger.debug(f"Final mapping: 0x{cob_id:03X} -> {info['type']} ({var_count} vars)")
    
    def start_collection(self):
        """Start collecting data from PDO messages"""
        try:
            if not self.interface_manager or not self.interface_manager.is_connected():
                self.logger.error("Cannot start data collection - interface not connected")
                return False
            
            if not self.pdo_variables:
                self.logger.warning("No PDO variables available for data collection")
                return False
            
            # Add message callback
            self.interface_manager.add_message_callback(self.on_message_received)
            
            # Start monitoring if not already started
            if not self.interface_manager.is_monitoring():
                if not self.interface_manager.start_monitoring():
                    self.logger.error("Failed to start monitoring for data collection")
                    return False
            
            self.is_monitoring = True
            self.logger.info("Started data collection for graphing")
            return True
            
        except Exception as ex:
            self.logger.error(f"Error starting data collection: {ex}")
            return False
    
    def stop_collection(self):
        """Stop collecting data"""
        try:
            if self.interface_manager:
                self.interface_manager.remove_message_callback(self.on_message_received)
            
            self.is_monitoring = False
            self.logger.info("Stopped data collection for graphing")
            
        except Exception as ex:
            self.logger.error(f"Error stopping data collection: {ex}")
    
    def clear_data(self):
        """Clear all collected data"""
        for var_index in self.variable_history:
            self.variable_history[var_index].clear()
        
        # Reset current values
        for var_index in self.pdo_variables:
            self.pdo_variables[var_index]['current_value'] = 'No data'
        
        self.logger.info("Cleared all graph data")
    
    def on_message_received(self, message: CANMessage):
        """Process received CAN messages for data collection"""
        try:
            # Only process PDO messages
            if not (isinstance(message.message_type, str) and 
                   (message.message_type.startswith("PDO") or 
                    message.message_type.startswith("RPDO") or 
                    message.message_type.startswith("TPDO"))):
                return
            
            self.process_pdo_message(message)
            
        except Exception as e:
            self.logger.error(f"Error processing message for graphs: {e}")
    
    def process_pdo_message(self, message: CANMessage):
        """Process PDO messages and store data for graphing"""
        try:
            cob_id = message.cob_id
            normalized_cob_id = cob_id & 0xFFF0  # Remove node ID
            
            if normalized_cob_id not in self.cob_id_to_pdo:
                return
            
            pdo_info = self.cob_id_to_pdo[normalized_cob_id]
            pdo_data = pdo_info['pdo_info']
            
            # Extract values for each mapped variable
            bit_offset = 0
            timestamp = message.timestamp
            
            for var in pdo_data['mapped_variables']:
                var_index = var['index']
                bit_length = var['bit_length']
                
                # Only process variables that exist in our list
                if var_index not in self.pdo_variables:
                    bit_offset += bit_length
                    continue
                
                # Calculate byte positions and extract value
                byte_start = bit_offset // 8
                byte_end = (bit_offset + bit_length - 1) // 8
                
                if byte_end < len(message.data):
                    value = self._extract_value(message.data, byte_start, bit_length, bit_offset)
                    if value is not None:
                        # Store data point
                        self.variable_history[var_index].append((timestamp, value))
                        
                        # Limit history size
                        if len(self.variable_history[var_index]) > self.max_history_points:
                            self.variable_history[var_index].pop(0)
                        
                        # Update current value
                        self.pdo_variables[var_index]['current_value'] = str(value)
                
                bit_offset += bit_length
            
        except Exception as e:
            self.logger.error(f"Error processing PDO message for graphs: {e}")
    
    def _extract_value(self, data, byte_start, bit_length, bit_offset):
        """Extract value from CAN data based on bit length"""
        try:
            if bit_length <= 8:
                value = data[byte_start]
                if bit_length < 8:
                    bit_pos = bit_offset % 8
                    mask = ((1 << bit_length) - 1) << bit_pos
                    value = (value & mask) >> bit_pos
            elif bit_length <= 16:
                if byte_start + 1 < len(data):
                    value = data[byte_start] | (data[byte_start + 1] << 8)
                else:
                    value = data[byte_start]
            elif bit_length <= 32:
                value = 0
                for i in range(min(4, len(data) - byte_start)):
                    value |= data[byte_start + i] << (i * 8)
            else:
                # Skip larger values for graphing
                return None
            
            return value
        except (IndexError, ValueError):
            return None
    
    def get_variable_data(self, var_index: str) -> List[Tuple]:
        """Get historical data for a specific variable"""
        return self.variable_history.get(var_index, [])
    
    def initialize_variable_history(self, var_index):
        """Initialize history for a variable"""
        if var_index not in self.variable_history:
            self.variable_history[var_index] = []
