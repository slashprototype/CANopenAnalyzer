import flet as ft
from typing import Any
import threading
import time

from .left_panel import LeftPanel
from .right_panel import RightPanel
from .tracked_variable import TrackedVariable
from managers.sdo_manager import SDOManager

# Add missing import for CANMessage
try:
    from ..can_interface.can_message import CANMessage
except ImportError:
    # Fallback if CANMessage is not available
    class CANMessage:
        def __init__(self, cob_id=0, data=None, message_type=""):
            self.cob_id = cob_id
            self.data = data or []
            self.message_type = message_type

class VariablesModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: Any = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.interface_manager = interface_manager
        self.od_reader_module = None  # Reference to OD reader module
        self.sdo_manager = None  # SDO manager instance

        # Create panels
        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

    def initialize(self):
        """Initialize the variables module"""
        # Initialize SDO manager
        if self.interface_manager:
            self.sdo_manager = SDOManager(self.interface_manager, self.logger)
            self.sdo_manager.start()
        
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
                        width=420,
                    ),
                    
                    ft.VerticalDivider(width=1),
                    
                    # Right panel (60%)
                    ft.Container(
                        content=self.right_panel,
                        width=None,
                        expand=True,
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
            if od_module and hasattr(od_module, "registers") and od_module.registers:
                # Patch: convert 'dataLength' to 'data_length' if needed
                registers = []
                for reg in od_module.registers:
                    reg_copy = dict(reg)
                    if "dataLength" in reg_copy:
                        reg_copy["data_length"] = reg_copy.pop("dataLength")
                    registers.append(reg_copy)
                self.left_panel.load_variables_from_od(registers)
                
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
        # Try to load variables immediately if registers are available
        if od_reader_module and hasattr(od_reader_module, "registers") and od_reader_module.registers:
            registers = []
            for reg in od_reader_module.registers:
                reg_copy = dict(reg)
                if "dataLength" in reg_copy:
                    reg_copy["data_length"] = reg_copy.pop("dataLength")
                registers.append(reg_copy)
            self.left_panel.load_variables_from_od(registers)
    
    def load_od_variables(self, od_module):
        """Load variables from OD reader module (using registers list)"""
        registers = []
        for reg in od_module.registers:
            reg_copy = dict(reg)
            if "dataLength" in reg_copy:
                reg_copy["data_length"] = reg_copy.pop("dataLength")
            registers.append(reg_copy)
        self.left_panel.load_variables_from_od(registers)
    
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
        """Read a variable value via SDO manager"""
        try:
            if not self.sdo_manager:
                self.logger.error("No SDO manager available")
                return False
            
            # Convert index to integer if it's a string
            if isinstance(variable.index, str):
                index_str = variable.index.replace('0x', '').replace('0X', '')
                index = int(index_str, 16)
            else:
                index = variable.index
            
            # Sub-index is always 0 as specified
            sub_index = 0

            # Create callback for SDO read response
            def sdo_read_callback(success: bool, message: str, value: int = None):
                try:
                    if success and value is not None:
                        # Update variable value
                        variable.update_value(value)
                        self.page.open(
                            ft.SnackBar(
                                content=ft.Text(f"Read successful for {variable.name}: {value}"),
                                bgcolor=ft.Colors.GREEN_400
                            )
                        )
                        self.logger.info(f"SDO read successful for {variable.name}: {value}")
                        
                        # Update the display
                        self.right_panel.update_table()
                    else:
                        self.page.open(
                            ft.SnackBar(
                                content=ft.Text(f"Read failed for {variable.name}: {message}"),
                                bgcolor=ft.Colors.RED_400
                            )
                        )
                        self.logger.error(f"SDO read failed for {variable.name}: {message}")
                except Exception as e:
                    self.logger.error(f"Error showing SDO read result: {e}")

            # Send SDO expedited read using SDO manager
            success = self.sdo_manager.send_sdo_expedited_read(
                node_id=node_id,
                index=index,
                sub_index=sub_index,
                callback=sdo_read_callback,
                timeout_ms=1000
            )
            
            if success:
                self.logger.info(f"SDO expedited read request sent for {variable.name} - Index: 0x{index:04X}")
            else:
                self.logger.error(f"Failed to send SDO expedited read request for {variable.name}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error reading variable {variable.name}: {e}")
            return False
    
    def write_variable(self, variable: TrackedVariable, value: int, node_id: int = 1) -> bool:
        """Write a variable value via SDO manager"""
        try:
            if not self.sdo_manager:
                self.logger.error("No SDO manager available")
                return False

            # Convert index to integer if it's a string
            if isinstance(variable.index, str):
                # Remove '0x' prefix if present and convert to int
                index_str = variable.index.replace('0x', '').replace('0X', '')
                index = int(index_str, 16)
            else:
                index = variable.index
            
            # Calculate data size in bits based on data_length (bytes)
            data_size_bits = variable.data_length * 8
            
            # Sub-index is always 0 as specified
            sub_index = 0

            # Create callback for SDO response
            def sdo_callback(success: bool, message: str, error_code: int = None):
                try:
                    if success:
                        self.page.open(
                            ft.SnackBar(
                                content=ft.Text(f"SDO write successful for {variable.name}"),
                                bgcolor=ft.Colors.GREEN_400
                            )
                        )
                        self.logger.info(f"SDO write successful for {variable.name}")
                    else:
                        self.page.open(
                            ft.SnackBar(
                                content=ft.Text(f"SDO write failed for {variable.name}: {message}"),
                                bgcolor=ft.Colors.RED_400
                            )
                        )
                        self.logger.error(f"SDO write failed for {variable.name}: {message}")
                except Exception as e:
                    self.logger.error(f"Error showing SDO result: {e}")

            # Send SDO expedited write using SDO manager
            success = self.sdo_manager.send_sdo_expedited_write(
                node_id=node_id,
                index=index,
                sub_index=sub_index,
                value=value,
                data_size=data_size_bits,
                callback=sdo_callback,
                timeout_ms=1000
            )
            
            if success:
                self.logger.info(f"SDO expedited write request sent for {variable.name} - Index: 0x{index:04X}, Value: {value}")
            else:
                self.logger.error(f"Failed to send SDO expedited write request for {variable.name}")
                
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
        return type_sizes.get(data_type.upper(), 8)  # Default to 32 bits
    
    def message_matches_variable(self, message: CANMessage, variable: TrackedVariable) -> bool:
        """Check if a CAN message corresponds to a tracked variable"""
        # Check for SDO response (COB-ID 0x580 + node_id)
        if message.cob_id >= 0x580 and message.cob_id <= 0x5FF:
            # Parse SDO response to check if it matches our variable
            if len(message.data) >= 4:
                try:
                    # SDO response format: [cmd, index_low, index_high, sub_index, data...]
                    index_from_msg = f"0x{message.data[2]:02X}{message.data[1]:02X}"
                    
                    var_index = variable.index.upper()
                    
                    return index_from_msg.upper() == var_index
                except:
                    return False
        
        # Add PDO mapping logic here if needed
        return False
    
    def extract_variable_value(self, message: CANMessage, variable: TrackedVariable) -> Any:
        """Extract variable value from CAN message"""
        try:
            if message.message_type == "SDO_RESPONSE" and len(message.data) >= 8:
                data_bytes = message.data[4:8]
                # Usa dataType si está disponible
                data_type = getattr(variable, "data_type", None) or getattr(variable, "dataType", None) or None
                if data_type:
                    data_type = data_type.upper()
                # Si no hay data_type, usa data_length
                if data_type in ("UNSIGNED8", "BOOLEAN", "INTEGER8", "SIGNED8"):
                    return data_bytes[0]
                elif data_type in ("UNSIGNED16", "INTEGER16", "SIGNED16"):
                    return data_bytes[0] | (data_bytes[1] << 8)
                elif data_type in ("UNSIGNED32", "INTEGER32", "SIGNED32", "REAL32"):
                    return (data_bytes[0] | (data_bytes[1] << 8) |
                            (data_bytes[2] << 16) | (data_bytes[3] << 24))
                elif hasattr(variable, "data_length"):
                    if variable.data_length == 1:
                        return data_bytes[0]
                    elif variable.data_length == 2:
                        return data_bytes[0] | (data_bytes[1] << 8)
                    elif variable.data_length == 4:
                        return (data_bytes[0] | (data_bytes[1] << 8) |
                                (data_bytes[2] << 16) | (data_bytes[3] << 24))
                    else:
                        return " ".join([f"{b:02X}" for b in data_bytes[:variable.data_length]])
                else:
                    return data_bytes[0]
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
    
    def set_interface_manager(self, interface_manager):
        """Set the interface manager from external module"""
        if self.interface_manager:
            self.interface_manager.remove_message_callback(self.on_message_received)
        
        self.interface_manager = interface_manager
        if self.interface_manager:
            self.interface_manager.add_message_callback(self.on_message_received)
            
        # Reinitialize SDO manager with new interface
        if self.sdo_manager:
            self.sdo_manager.stop()
        
        if self.interface_manager:
            self.sdo_manager = SDOManager(self.interface_manager, self.logger)
            self.sdo_manager.start()
