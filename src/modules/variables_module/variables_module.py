import flet as ft
from typing import Any
import threading
import time

from interfaces import InterfaceManager, CANMessage
from .left_panel import LeftPanel
from .right_panel import RightPanel
from .tracked_variable import TrackedVariable

class VariablesModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: InterfaceManager = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        self.is_monitoring = False
        self.od_reader_module = None  # Reference to OD reader module
        
        # Create panels
        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)
        
    def initialize(self):
        """Initialize the variables module"""
        # Register for CAN messages
        if self.interface_manager:
            self.interface_manager.add_message_callback(self.on_message_received)
        
        # Ensure proper parent references
        self.left_panel.parent = self
        self.right_panel.parent = self
        
        # Initialize panels first
        self.left_panel.initialize()
        self.right_panel.initialize()
        
        self.controls = [
            ft.Container(
                content=ft.Row([
                    # Left panel (40%)
                    ft.Container(
                        content=self.left_panel,
                        width=None,
                        expand=2
                    ),
                    
                    ft.VerticalDivider(width=1),
                    
                    # Right panel (60%)
                    ft.Container(
                        content=self.right_panel,
                        width=None,
                        expand=3,
                        padding=ft.padding.only(left=10)
                    )
                ], expand=True),
                padding=20,
                expand=True
            )
        ]
        self.expand = True
        
        # Start monitoring thread
        self.start_value_update_thread()
        
        # Try to auto-load from OD reader if available
        self.auto_load_from_od_reader()
    
    def auto_load_from_od_reader(self):
        """Automatically load variables from OD reader if available"""
        try:
            od_module = self.get_od_reader_module()
            if od_module and od_module.parser:
                self.load_od_variables(od_module)
                self.logger.info("Automatically loaded variables from OD Reader module")
        except Exception as e:
            self.logger.debug(f"Could not auto-load from OD reader: {e}")
    
    def get_od_reader_module(self):
        """Get reference to OD reader module from main app"""
        # This will be set by the main application
        return self.od_reader_module
    
    def set_od_reader_module(self, od_reader_module):
        """Set reference to OD reader module"""
        self.od_reader_module = od_reader_module
        # Try to load variables immediately if parser is available
        if od_reader_module and od_reader_module.parser:
            self.load_od_variables(od_reader_module)
    
    def load_od_variables(self, od_module):
        """Load variables from OD reader module"""
        self.left_panel.load_variables_from_od(od_module)
    
    def on_message_received(self, message: CANMessage):
        """Process received CAN messages to update variable values"""
        try:
            # Check if this message corresponds to any tracked variables
            for var in self.right_panel.tracked_variables:
                if self.message_matches_variable(message, var):
                    # Extract value from message data based on variable type
                    value = self.extract_variable_value(message, var)
                    if value is not None:
                        var.update_value(value)
                        
        except Exception as e:
            self.logger.error(f"Error processing message for variables: {e}")
    
    def read_variable(self, variable: TrackedVariable, node_id: int = 1) -> bool:
        """Read a variable value via SDO"""
        try:
            if not self.interface_manager:
                self.logger.error("No interface manager available")
                return False
            
            # Convert index and sub_index to integers
            index = int(variable.index.replace('0x', ''), 16) if isinstance(variable.index, str) else variable.index
            sub_index = int(variable.sub_index.replace('0x', ''), 16) if isinstance(variable.sub_index, str) else variable.sub_index
            
            # Send SDO read
            success = self.interface_manager.send_sdo_read(node_id, index, sub_index)
            
            if success:
                self.logger.info(f"SDO read request sent for {variable.name}")
            else:
                self.logger.error(f"Failed to send SDO read for {variable.name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error reading variable {variable.name}: {e}")
            return False
    
    def write_variable(self, variable: TrackedVariable, value: int, node_id: int = 1) -> bool:
        """Write a variable value via SDO expedited transfer"""
        try:
            if not self.interface_manager:
                self.logger.error("No interface manager available")
                return False
            
            # Convert index and sub_index to integers
            index = int(variable.index.replace('0x', ''), 16) if isinstance(variable.index, str) else variable.index
            sub_index = int(variable.sub_index.replace('0x', ''), 16) if isinstance(variable.sub_index, str) else variable.sub_index
            
            # Determine data size based on variable type
            data_size = self._get_data_size_for_type(variable.data_type)
            
            # Send SDO expedited write
            success = self.interface_manager.send_sdo_expedited(node_id, index, sub_index, value, data_size)
            
            if success:
                self.logger.info(f"SDO expedited write sent for {variable.name}")
            else:
                self.logger.error(f"Failed to send SDO expedited write for {variable.name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error writing variable {variable.name}: {e}")
            return False
    
    def _get_data_size_for_type(self, data_type: str) -> int:
        """Get data size in bits based on data type"""
        type_sizes = {
            'BOOLEAN': 8,
            'UNSIGNED8': 8,
            'INTEGER8': 8,
            'SIGNED8': 8,
            'UNSIGNED16': 16,
            'INTEGER16': 16,
            'SIGNED16': 16,
            'UNSIGNED32': 32,
            'INTEGER32': 32,
            'SIGNED32': 32,
            'REAL32': 32
        }
        return type_sizes.get(data_type.upper(), 32)  # Default to 32 bits
    
    def message_matches_variable(self, message: CANMessage, variable: TrackedVariable) -> bool:
        """Check if a CAN message corresponds to a tracked variable"""
        # Check for SDO response (COB-ID 0x580 + node_id)
        if message.cob_id >= 0x580 and message.cob_id <= 0x5FF:
            # Parse SDO response to check if it matches our variable
            if len(message.data) >= 4:
                try:
                    # SDO response format: [cmd, index_low, index_high, sub_index, data...]
                    index_from_msg = f"{message.data[2]:02X}{message.data[1]:02X}"
                    sub_index_from_msg = f"{message.data[3]:02X}"
                    
                    var_index = variable.index.replace('0x', '').upper()
                    var_sub_index = variable.sub_index.replace('0x', '').upper()
                    
                    return (index_from_msg.upper() == var_index and 
                            sub_index_from_msg.upper() == var_sub_index)
                except:
                    return False
        
        # Add PDO mapping logic here if needed
        return False
    
    def extract_variable_value(self, message: CANMessage, variable: TrackedVariable) -> Any:
        """Extract variable value from CAN message"""
        try:
            if message.message_type == "SDO_RESPONSE" and len(message.data) >= 8:
                # Extract value from SDO response (bytes 4-7)
                data_bytes = message.data[4:8]
                
                # Convert based on data type
                if variable.data_type in ["UNSIGNED8", "BOOLEAN"]:
                    return data_bytes[0]
                elif variable.data_type == "UNSIGNED16":
                    return data_bytes[0] | (data_bytes[1] << 8)
                elif variable.data_type == "UNSIGNED32":
                    return (data_bytes[0] | (data_bytes[1] << 8) | 
                           (data_bytes[2] << 16) | (data_bytes[3] << 24))
                elif variable.data_type in ["INTEGER8", "SIGNED8"]:
                    return data_bytes[0] if data_bytes[0] < 128 else data_bytes[0] - 256
                elif variable.data_type in ["INTEGER16", "SIGNED16"]:
                    val = data_bytes[0] | (data_bytes[1] << 8)
                    return val if val < 32768 else val - 65536
                elif variable.data_type in ["INTEGER32", "SIGNED32"]:
                    val = (data_bytes[0] | (data_bytes[1] << 8) | 
                          (data_bytes[2] << 16) | (data_bytes[3] << 24))
                    return val if val < 2147483648 else val - 4294967296
                else:
                    # Return raw hex for unknown types
                    return " ".join([f"{b:02X}" for b in data_bytes])
        except Exception as e:
            self.logger.error(f"Error extracting variable value: {e}")
        
        return None
    
    def start_value_update_thread(self):
        """Start thread to periodically update variable display"""
        def update_display():
            while True:
                try:
                    if self.right_panel.tracked_variables:
                        self.right_panel.update_table()
                    time.sleep(1)  # Update every second
                except Exception as e:
                    self.logger.error(f"Error in value update thread: {e}")
                    break
        
        update_thread = threading.Thread(target=update_display)
        update_thread.daemon = True
        update_thread.start()
    
    def set_interface_manager(self, interface_manager: InterfaceManager):
        """Set the interface manager from external module"""
        if self.interface_manager:
            self.interface_manager.remove_message_callback(self.on_message_received)
        
        self.interface_manager = interface_manager
        if self.interface_manager:
            self.interface_manager.add_message_callback(self.on_message_received)
