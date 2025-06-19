"""
Factory for creating different CAN interface implementations
"""

from typing import Optional
from .base_interface import BaseCANInterface
from .usb_serial_interface import USBSerialCANInterface

# Try to import the original CANopen analyzer, fallback if not available
try:
    from ..analyzer.canopen_analyzer import CANopenAnalyzer as OriginalCANopenAnalyzer
    CANOPEN_AVAILABLE = True
except ImportError:
    CANOPEN_AVAILABLE = False

class CANInterfaceFactory:
    """Factory for creating CAN interface instances"""
    
    @staticmethod
    def create_interface(interface_type: str, **kwargs) -> Optional[BaseCANInterface]:
        """
        Create a CAN interface instance based on type
        
        Args:
            interface_type: Type of interface ("socketcan", "usb_serial")
            **kwargs: Interface-specific configuration parameters
            
        Returns:
            BaseCANInterface instance or None if creation fails
        """
        
        if interface_type.lower() == "usb_serial":
            com_port = kwargs.get('com_port', 'COM1')
            baudrate = kwargs.get('serial_baudrate', 115200)
            return USBSerialCANInterface(com_port=com_port, baudrate=baudrate)
            
        elif interface_type.lower() == "socketcan" and CANOPEN_AVAILABLE:
            # Wrapper for original CANopen analyzer to match interface
            return SocketCANWrapper(**kwargs)
            
        else:
            print(f"Unknown interface type: {interface_type}")
            return None
    
    @staticmethod
    def get_available_interfaces() -> list:
        """Get list of available interface types"""
        interfaces = ["usb_serial"]
        if CANOPEN_AVAILABLE:
            interfaces.append("socketcan")
        return interfaces

if CANOPEN_AVAILABLE:
    class SocketCANWrapper(BaseCANInterface):
        """Wrapper to make original CANopenAnalyzer compatible with interface"""
        
        def __init__(self, interface: str = "socketcan", channel: str = "can0", bitrate: int = 125000):
            super().__init__()
            self.analyzer = OriginalCANopenAnalyzer(interface, channel, bitrate)
            
        def connect(self, **kwargs) -> bool:
            """Connect to CAN interface"""
            result = self.analyzer.connect()
            self.is_connected = result
            return result
        
        def disconnect(self):
            """Disconnect from CAN interface"""
            self.analyzer.disconnect()
            self.is_connected = False
        
        def start_monitoring(self) -> bool:
            """Start monitoring CAN messages"""
            if not self.is_connected:
                return False
            result = self.analyzer.start_monitoring()
            self.is_monitoring = result
            # Add callback to convert messages to our format
            self.analyzer.add_message_callback(self._convert_message)
            return result
        
        def stop_monitoring(self):
            """Stop monitoring CAN messages"""
            self.analyzer.stop_monitoring()
            self.is_monitoring = False
        
        def send_data(self, send_data) -> bool:
            """Send data through CAN interface"""
            # This would need to be implemented based on original analyzer's send capabilities
            print("SocketCAN send_data not implemented yet")
            return False
        
        def _convert_message(self, original_message):
            """Convert original CANMessage to our format"""
            # Convert the original message format to our CANMessage format
            from .base_interface import CANMessage
            
            can_message = CANMessage(
                timestamp=original_message.timestamp,
                cob_id=original_message.cob_id,
                node_id=original_message.node_id,
                function_code=original_message.function_code,
                data=list(original_message.data),
                message_type=original_message.message_type,
                length=original_message.length,
                raw_data=original_message.data
            )
            
            # Add to our message history
            self.message_history.append(can_message)
            if len(self.message_history) > 1000:
                self.message_history.pop(0)
            
            # Update message stack (simplified)
            frame_id_str = f'{original_message.cob_id:03X}'
            self.message_stack[frame_id_str] = list(original_message.data)
            
            # Notify our callbacks
            self._notify_callbacks(can_message)
