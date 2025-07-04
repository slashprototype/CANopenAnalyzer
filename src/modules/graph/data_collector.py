import time
import threading
from typing import Dict, List, Tuple, Callable
from interfaces import CANMessage, InterfaceManager

class DataCollector:
    def __init__(self, logger, interface_manager):
        self.logger = logger
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        
        # Data storage
        self.variable_history = {}  # {var_index: [(timestamp, value), ...]}
        self.max_history_points = 1000
        self.is_monitoring = False
        self.is_collecting = False
        
        # PDO mappings
        self.cob_id_to_pdo = {}
        self.pdo_variables = {}
        
        # Callbacks for graph updates
        self.update_callbacks = []
        self.debug_callbacks = []
        
        # Node filtering
        self.monitored_node_id = 2  # Default node ID to monitor
        self.selected_node_id = 2
        
        # Additional attributes
        self.collected_data = {}
        self.data_table = None
        self.last_update_time = time.time()
        self.messages_since_last_update = 0
        self.page = None
        self.control_buttons = None
        
        # Debug counters
        self.debug_stats = {
            "total_messages": 0,
            "pdo_messages": 0,
            "processed_pdos": 0,
            "variables_updated": 0,
            "last_pdo_cob_id": None,
            "last_pdo_node_id": None
        }
        
        # NUEVO: Sistema de polling optimizado
        self._polling_thread = None
        self._polling_active = False
        self._last_poll_timestamp = 0
        self._poll_interval = 0.05  # 50ms polling interval
        self._message_cache = {}
        
        # Additional attributes for throttling
        self.last_notification_time = 0
        self.notification_interval = 0.5  # AUMENTADO: 500ms entre notificaciones
        self.batch_update_counter = 0
        self.batch_size = 100  # AUMENTADO: notificar cada 100 variables procesadas
    
    def add_update_callback(self, callback: Callable):
        """Add callback for when data is updated"""
        if callback not in self.update_callbacks:
            self.update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable):
        """Remove data update callback"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    def _notify_data_update(self):
        """Notify all callbacks about data updates"""
        for callback in self.update_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in data update callback: {e}")

    def add_debug_callback(self, callback):
        """Add callback for debug information"""
        if callback not in self.debug_callbacks:
            self.debug_callbacks.append(callback)
    
    def remove_debug_callback(self, callback):
        """Remove debug callback"""
        if callback in self.debug_callbacks:
            self.debug_callbacks.remove(callback)
    
    def _notify_debug(self, debug_info: dict):
        """Notify debug callbacks"""
        for callback in self.debug_callbacks:
            try:
                callback(debug_info)
            except Exception as e:
                self.logger.error(f"Error in debug callback: {e}")

    def set_monitored_node_id(self, node_id: int):
        """Set the node ID to monitor for PDO messages"""
        self.monitored_node_id = node_id
        self.logger.info(f"Data collector - monitoring node ID set to: {node_id}")
    
    def set_pdo_variables(self, pdo_variables: dict):
        """Set the PDO variables dictionary for tracking"""
        self.pdo_variables = pdo_variables
        self.logger.info(f"Data collector - PDO variables set: {len(pdo_variables)} variables")
    
    def build_cob_id_mapping(self, pdo_mappings):
        """Build mapping from COB-ID to PDO information for quick lookup"""
        self.cob_id_to_pdo = {}
        
        self.logger.info(f"🔍 DEBUG: Building COB-ID mapping from PDO mappings: {type(pdo_mappings)}")
        
        if isinstance(pdo_mappings, dict):
            # Process RPDOs and TPDOs
            rpdos = pdo_mappings.get('rpdos', [])
            tpdos = pdo_mappings.get('tpdos', [])
            
            self.logger.info(f"🔍 DEBUG: Found {len(rpdos)} RPDOs and {len(tpdos)} TPDOs")
            
            for rpdo in rpdos:
                if rpdo.get('enabled') and rpdo.get('mapped_variables'):
                    cob_id = rpdo.get('cob_id_clean')
                    if cob_id is not None:
                        self.cob_id_to_pdo[cob_id] = {
                            'type': 'RPDO',
                            'pdo_info': rpdo
                        }
                        # Debug: Log variable indices in this PDO
                        var_indices = [var['index'] for var in rpdo['mapped_variables']]
                        self.logger.info(f"🔍 DEBUG: Added RPDO mapping: COB-ID 0x{cob_id:03X} with variables: {var_indices}")
            
            for tpdo in tpdos:
                if tpdo.get('enabled') and tpdo.get('mapped_variables'):
                    cob_id = tpdo.get('cob_id_clean')
                    if cob_id is not None:
                        self.cob_id_to_pdo[cob_id] = {
                            'type': 'TPDO',
                            'pdo_info': tpdo
                        }
                        # Debug: Log variable indices in this PDO
                        var_indices = [var['index'] for var in tpdo['mapped_variables']]
                        self.logger.info(f"🔍 DEBUG: Added TPDO mapping: COB-ID 0x{cob_id:03X} with variables: {var_indices}")
        
        else:
            self.logger.warning(f"🔍 DEBUG: Unexpected PDO mappings format: {type(pdo_mappings)}")
        
        self.logger.info(f"🔍 DEBUG: Built COB-ID mapping for {len(self.cob_id_to_pdo)} enabled PDOs")
        
        # Log the final mapping for debugging
        for cob_id, info in self.cob_id_to_pdo.items():
            var_count = len(info['pdo_info'].get('mapped_variables', []))
            self.logger.info(f"🔍 DEBUG: Final mapping: 0x{cob_id:03X} -> {info['type']} ({var_count} vars)")
    
    def start_collection(self):
        """Start data collection with optimized polling"""
        try:
            if not self.interface_manager or not self.interface_manager.is_connected():
                self.logger.error("Cannot start collection - interface not connected")
                return False
            
            if self.is_collecting:
                self.logger.warning("Collection already in progress")
                return False
            
            # Clear existing data
            self.collected_data.clear()
            self.variable_history.clear()
            
            if self.data_table is not None and hasattr(self.data_table, 'rows'):
                self.data_table.rows.clear()
            
            self.last_update_time = time.time()
            self.messages_since_last_update = 0
            self._last_poll_timestamp = time.time()
            
            # CAMBIADO: Usar polling en lugar de callbacks
            # No registrar callback, usar thread de polling
            self._polling_active = True
            self._polling_thread = threading.Thread(target=self._polling_loop)
            self._polling_thread.daemon = True
            self._polling_thread.start()
            
            # Start monitoring if not already started
            if not self.interface_manager.is_monitoring():
                if not self.interface_manager.start_monitoring():
                    self.logger.error("Failed to start monitoring for data collection")
                    return False
            
            self.is_collecting = True
            self.logger.info("Data collection started with optimized polling")
            return True
                
        except Exception as ex:
            self.logger.error(f"Error starting data collection: {ex}")
            return False

    def stop_collection(self):
        """Stop data collection"""
        try:
            # Stop polling thread
            self._polling_active = False
            if self._polling_thread and self._polling_thread.is_alive():
                self._polling_thread.join(timeout=1.0)
            
            self.is_collecting = False
            self.logger.info("Data collection stopped")
            return True
                
        except Exception as ex:
            self.logger.error(f"Error stopping data collection: {ex}")
            return False
    
    def clear_data(self):
        """Clear all collected data"""
        for var_index in self.variable_history:
            self.variable_history[var_index].clear()
        
        # Reset current values
        for var_index in self.pdo_variables:
            self.pdo_variables[var_index]['current_value'] = 'No data'
        
        self.logger.info("Cleared all graph data")
    
    def _polling_loop(self):
        """Optimized polling loop for message processing"""
        self.logger.info("🔍 DEBUG: DataCollector polling loop started")
        try:
            while self._polling_active and self.is_collecting:
                current_time = time.time()
                
                # Get new messages since last poll
                if hasattr(self.interface_manager, 'get_messages_since'):
                    new_messages = self.interface_manager.get_messages_since(self._last_poll_timestamp)
                    
                    if new_messages:
                        self.logger.info(f"🔍 DEBUG: DataCollector received {len(new_messages)} new messages")
                        # Process messages in batch
                        self._process_message_batch(new_messages)
                        self._last_poll_timestamp = current_time
                        
                        # Update statistics
                        self.debug_stats["total_messages"] += len(new_messages)
                        self.messages_since_last_update += len(new_messages)
                else:
                    # Fallback to old method if interface doesn't support new polling
                    self.logger.warning("🔍 DEBUG: Interface doesn't support get_messages_since, using fallback")
                    self._fallback_polling()
                
                # Throttled notifications
                if (current_time - self.last_notification_time) >= self.notification_interval:
                    self.last_notification_time = current_time
                    variables_count = len(self.variable_history)
                    self.logger.info(f"🔍 DEBUG: DataCollector notifying update - {variables_count} variables tracked")
                    self._notify_data_update()
                
                # Sleep for poll interval
                time.sleep(self._poll_interval)
                
        except Exception as e:
            self.logger.error(f"Error in polling loop: {e}")
    
    def _process_message_batch(self, messages: List[CANMessage]):
        """Process batch of messages efficiently"""
        pdo_messages = []
        
        self.logger.info(f"🔍 DEBUG: Processing message batch of {len(messages)} messages")
        
        # Filter PDO messages first
        for message in messages:
            # Only process if we have a selected node and it matches
            if self.selected_node_id != 0 and message.node_id != self.selected_node_id:
                continue
                
            if (isinstance(message.message_type, str) and 
                (message.message_type.startswith("PDO") or 
                 message.message_type.startswith("RPDO") or 
                 message.message_type.startswith("TPDO"))):
                pdo_messages.append(message)
                self.logger.info(f"🔍 DEBUG: Found PDO message: {message.message_type}, COB-ID: 0x{message.cob_id:03X}")
        
        # Process PDO messages in batch
        if pdo_messages:
            self.debug_stats["pdo_messages"] += len(pdo_messages)
            self.logger.info(f"🔍 DEBUG: Processing {len(pdo_messages)} PDO messages")
            self._process_pdo_batch(pdo_messages)
        else:
            self.logger.warning(f"🔍 DEBUG: No PDO messages found in batch of {len(messages)} messages")
    
    def _process_pdo_batch(self, messages: List[CANMessage]):
        """Process batch of PDO messages efficiently"""
        variables_updated = 0
        
        for message in messages:
            updated_count = self._process_single_pdo_optimized(message)
            variables_updated += updated_count
            if updated_count > 0:
                self.logger.info(f"🔍 DEBUG: Updated {updated_count} variables from COB-ID 0x{message.cob_id:03X}")
        
        if variables_updated > 0:
            self.debug_stats["variables_updated"] += variables_updated
            self.batch_update_counter += variables_updated
            self.logger.info(f"🔍 DEBUG: Total variables updated in batch: {variables_updated}")
        else:
            self.logger.warning("🔍 DEBUG: No variables were updated in this PDO batch")
    
    def _process_single_pdo_optimized(self, message: CANMessage) -> int:
        """Optimized processing of single PDO message"""
        try:
            cob_id = message.cob_id
            node_id = cob_id & 0xF
            
            self.logger.info(f"🔍 DEBUG: Processing PDO - COB-ID: 0x{cob_id:03X}, Node: {node_id}, Data: {message.data}")
            
            if self.monitored_node_id != 0 and node_id != self.monitored_node_id:
                self.logger.info(f"🔍 DEBUG: Skipping message - node {node_id} != monitored {self.monitored_node_id}")
                return 0
            
            # Quick PDO mapping lookup
            pdo_info = self._get_pdo_info_optimized(cob_id)
            if not pdo_info:
                self.logger.warning(f"🔍 DEBUG: No PDO mapping found for COB-ID 0x{cob_id:03X}")
                # Log available mappings for debugging
                available_cob_ids = list(self.cob_id_to_pdo.keys())
                self.logger.info(f"🔍 DEBUG: Available COB-IDs: {[f'0x{x:03X}' for x in available_cob_ids]}")
                return 0
            
            self.debug_stats["processed_pdos"] += 1
            pdo_data = pdo_info['pdo_info']
            
            self.logger.info(f"🔍 DEBUG: Found PDO mapping: {pdo_info['type']} with {len(pdo_data.get('mapped_variables', []))} variables")
            
            # Extract values efficiently
            bit_offset = 0
            variables_updated_count = 0
            timestamp = message.timestamp.timestamp()
            
            for var in pdo_data['mapped_variables']:
                var_index = var['index']
                bit_length = var['bit_length']
                
                self.logger.info(f"🔍 DEBUG: Processing variable {var_index}, bit_offset: {bit_offset}, bit_length: {bit_length}")
                
                value = self._extract_value_improved(message.data, bit_offset, bit_length)
                
                if value is not None:
                    # Batch update variable history
                    self._update_variable_history_optimized(var_index, timestamp, value)
                    variables_updated_count += 1
                    self.logger.info(f"🔍 DEBUG: Updated variable {var_index} = {value}")
                else:
                    self.logger.warning(f"🔍 DEBUG: Failed to extract value for variable {var_index}")
                
                bit_offset += bit_length
            
            self.logger.info(f"🔍 DEBUG: Processed PDO successfully, updated {variables_updated_count} variables")
            return variables_updated_count
            
        except Exception as e:
            self.logger.error(f"🔍 DEBUG: Error in _process_single_pdo_optimized: {e}")
            import traceback
            self.logger.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            return 0
    
    def _extract_value_improved(self, data, bit_offset, bit_length):
        """Improved value extraction from CAN data with debugging"""
        try:
            self.logger.debug(f"🔍 DEBUG: Extracting value - data: {data}, bit_offset: {bit_offset}, bit_length: {bit_length}")
            
            byte_start = bit_offset // 8
            bit_pos_in_byte = bit_offset % 8
            
            if byte_start >= len(data):
                self.logger.warning(f"🔍 DEBUG: byte_start {byte_start} >= data length {len(data)}")
                return None
            
            if bit_length <= 8:
                # Single byte value
                value = data[byte_start]
                if bit_length < 8:
                    # Extract specific bits
                    mask = (1 << bit_length) - 1
                    value = (value >> bit_pos_in_byte) & mask
                self.logger.debug(f"🔍 DEBUG: Extracted 8-bit value: {value}")
            elif bit_length <= 16:
                # Two byte value (little endian)
                if byte_start + 1 < len(data):
                    value = data[byte_start] | (data[byte_start + 1] << 8)
                else:
                    value = data[byte_start]
                self.logger.debug(f"🔍 DEBUG: Extracted 16-bit value: {value}")
            elif bit_length <= 32:
                # Four byte value (little endian)
                value = 0
                for i in range(min(4, len(data) - byte_start)):
                    value |= data[byte_start + i] << (i * 8)
                self.logger.debug(f"🔍 DEBUG: Extracted 32-bit value: {value}")
            else:
                # Skip larger values for graphing
                self.logger.warning(f"🔍 DEBUG: Skipping value with bit_length {bit_length} (too large)")
                return None
            
            return value
            
        except (IndexError, ValueError, TypeError) as e:
            self.logger.error(f"🔍 DEBUG: Error extracting value at bit_offset={bit_offset}, bit_length={bit_length}: {e}")
            return None
    
    def _get_pdo_info_optimized(self, cob_id):
        """Get PDO information for a given COB-ID"""
        return self.cob_id_to_pdo.get(cob_id)
    
    def _update_variable_history_optimized(self, var_index, timestamp, value):
        """Update variable history with new value"""
        try:
            # Initialize history if needed
            if var_index not in self.variable_history:
                self.variable_history[var_index] = []
            
            # Add new data point
            self.variable_history[var_index].append((timestamp, value))
            
            # Limit history size
            if len(self.variable_history[var_index]) > self.max_history_points:
                self.variable_history[var_index] = self.variable_history[var_index][-self.max_history_points:]
            
            # Update current value in pdo_variables if it exists
            if var_index in self.pdo_variables:
                self.pdo_variables[var_index]['current_value'] = value
                
        except Exception as e:
            self.logger.error(f"Error updating variable history for {var_index}: {e}")
    
    def _fallback_polling(self):
        """Fallback polling method for older interfaces"""
        self.logger.info("🔍 DEBUG: Using fallback polling method")
        # Get latest messages using old method
        if hasattr(self.interface_manager, 'get_latest_messages'):
            messages = self.interface_manager.get_latest_messages(100)
            self.logger.info(f"🔍 DEBUG: Fallback got {len(messages)} messages")
            # Filter to new messages only
            current_time = time.time()
            new_messages = [msg for msg in messages 
                          if hasattr(msg, 'timestamp') and 
                          msg.timestamp.timestamp() > self._last_poll_timestamp]
            
            if new_messages:
                self.logger.info(f"🔍 DEBUG: Fallback processing {len(new_messages)} new messages")
                self._process_message_batch(new_messages)
                self._last_poll_timestamp = current_time
        else:
            self.logger.warning("🔍 DEBUG: Interface doesn't have get_latest_messages method either")
    
    def get_variable_data(self, var_index: str) -> List[Tuple]:
        """Get historical data for a specific variable"""
        return self.variable_history.get(var_index, [])
    
    def initialize(self):
        """Initialize the data collector module"""
        # Register for connection state changes
        if self.interface_manager:
            self.interface_manager.add_connection_callback(self.update_connection_status)
        
        self.build_interface()
    
    def initialize_variable_history(self, var_index):
        """Initialize history for a variable"""
        if var_index not in self.variable_history:
            self.variable_history[var_index] = []
            self.logger.debug(f"Initialized history for variable: {var_index}")
        else:
            self.logger.debug(f"Variable {var_index} history already exists")
    
    def get_debug_stats(self):
        """Get current debug statistics"""
        return self.debug_stats.copy()
    
    def update_connection_status(self, connected: bool):
        """Update connection status display (called from interface manager)"""
        print(f"DEBUG: Data collector - received connection status callback: {connected}")
        if not connected:
            # Stop collection if disconnected
            if self.is_collecting:
                self.stop_collection()
        
        self.update_button_states()
        if self.page:
            self.page.update()

    def update_button_states(self):
        """Update button enabled/disabled states"""
        print(f"DEBUG: Data collector - updating button states. Connected: {self.interface_manager.is_connected() if self.interface_manager else False}, Collecting: {self.is_collecting}")
        if self.control_buttons and len(self.control_buttons.controls) >= 2:
            start_button = self.control_buttons.controls[0]
            stop_button = self.control_buttons.controls[1]
            
            is_connected = self.interface_manager.is_connected() if self.interface_manager else False
            start_button.disabled = not is_connected or self.is_collecting
            stop_button.disabled = not self.is_collecting
            
            if self.page:
                self.page.update()
    
    # Add missing methods that were referenced but not defined
    def build_interface(self):
        """Build interface (placeholder - implement if needed)"""
        pass
    
    def update_data_table(self):
        """Update data table (placeholder - implement if needed)"""
        pass
    
    def start_stats_update(self):
        """Start statistics update (placeholder - implement if needed)"""
        pass
    
    def set_interface_manager(self, interface_manager: InterfaceManager):
        """Set the interface manager"""
        self.interface_manager = interface_manager
        if interface_manager:
            interface_manager.add_connection_callback(self.update_connection_status)