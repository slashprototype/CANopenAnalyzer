"""
Interface manager for handling different CAN communication methods
"""

from typing import Optional, Dict, Any, Callable, List
from config.app_config import AppConfig
from interfaces import CANInterfaceFactory, BaseCANInterface, CANMessage
from utils.logger import Logger

class InterfaceManager:
    """Manages CAN interface selection and operations - Singleton"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config: AppConfig = None, logger: Logger = None):
        if cls._instance is None:
            cls._instance = super(InterfaceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: AppConfig = None, logger: Logger = None):
        # Only initialize once
        if self._initialized:
            return
            
        if config is None or logger is None:
            raise ValueError("config and logger must be provided for first initialization")
            
        self.config = config
        self.logger = logger
        self.current_interface: Optional[BaseCANInterface] = None
        self.interface_type: str = config.can_config.interface
        self.connection_callbacks: List[Callable[[bool], None]] = []
        self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            raise RuntimeError("InterfaceManager not initialized. Call with config and logger first.")
        return cls._instance
    
    def add_connection_callback(self, callback: Callable[[bool], None]):
        """Add callback for connection state changes"""
        if callback not in self.connection_callbacks:
            self.connection_callbacks.append(callback)
    
    def remove_connection_callback(self, callback: Callable[[bool], None]):
        """Remove connection state callback"""
        if callback in self.connection_callbacks:
            self.connection_callbacks.remove(callback)
    
    def _notify_connection_change(self, connected: bool):
        """Notify all registered callbacks about connection state change"""
        print(f"DEBUG: InterfaceManager notifying {len(self.connection_callbacks)} callbacks about connection: {connected}")
        for callback in self.connection_callbacks:
            try:
                callback(connected)
            except Exception as e:
                self.logger.error(f"Error in connection callback: {e}")
    
    def initialize_interface(self) -> bool:
        """Initialize the CAN interface based on configuration"""
        try:
            # Get interface parameters from config
            interface_params = self._get_interface_params()
            
            # Create interface instance
            self.current_interface = CANInterfaceFactory.create_interface(
                self.interface_type, 
                **interface_params
            )
            
            if self.current_interface is None:
                self.logger.error(f"Failed to create interface: {self.interface_type}")
                return False
                
            self.logger.info(f"Interface {self.interface_type} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing interface: {e}")
            return False
    
    def _get_interface_params(self) -> Dict[str, Any]:
        """Get interface-specific parameters from configuration"""
        params = {}
        
        if self.interface_type == "usb_serial":
            params.update({
                'com_port': self.config.can_config.com_port,
                'baudrate': self.config.can_config.serial_baudrate
            })
        elif self.interface_type == "socketcan":
            params.update({
                'interface': self.config.can_config.interface,
                'channel': self.config.can_config.channel,
                'bitrate': self.config.can_config.bitrate
            })
            
        return params
    
    def connect(self) -> bool:
        """Connect to the CAN interface"""
        if not self.current_interface:
            self.logger.error("No interface initialized")
            return False
            
        try:
            result = self.current_interface.connect(**self._get_interface_params())
            if result:
                self.logger.info(f"Connected to {self.interface_type} interface")
                self._notify_connection_change(True)
            else:
                self.logger.error(f"Failed to connect to {self.interface_type} interface")
                self._notify_connection_change(False)
            return result
        except Exception as e:
            self.logger.error(f"Error connecting to interface: {e}")
            self._notify_connection_change(False)
            return False
    
    def disconnect(self):
        """Disconnect from the CAN interface"""
        if self.current_interface:
            try:
                self.current_interface.disconnect()
                self.logger.info("Disconnected from CAN interface")
                self._notify_connection_change(False)
            except Exception as e:
                self.logger.error(f"Error disconnecting from interface: {e}")
    
    def start_monitoring(self) -> bool:
        """Start monitoring CAN messages"""
        if not self.current_interface:
            self.logger.error("No interface available for monitoring")
            return False
            
        try:
            result = self.current_interface.start_monitoring()
            if result:
                self.logger.info("Message monitoring started")
            else:
                self.logger.error("Failed to start message monitoring")
            return result
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop monitoring CAN messages"""
        if self.current_interface:
            try:
                self.current_interface.stop_monitoring()
                self.logger.info("Message monitoring stopped")
            except Exception as e:
                self.logger.error(f"Error stopping monitoring: {e}")
    
    def send_data(self, send_data: Dict[str, Any]) -> bool:
        """Send data through the current interface"""
        if not self.current_interface:
            self.logger.error("No interface available for sending data")
            return False
            
        try:
            result = self.current_interface.send_data(send_data)
            if result:
                self.logger.info(f"Data sent successfully: {send_data}")
            else:
                self.logger.error(f"Failed to send data: {send_data}")
            return result
        except Exception as e:
            self.logger.error(f"Error sending data: {e}")
            return False
    
    def add_message_callback(self, callback: Callable[[CANMessage], None]):
        """Add callback for new CAN messages"""
        if self.current_interface:
            self.current_interface.add_message_callback(callback)
    
    def remove_message_callback(self, callback: Callable[[CANMessage], None]):
        """Remove message callback"""
        if self.current_interface:
            self.current_interface.remove_message_callback(callback)
    
    def get_message_history(self):
        """Get message history from current interface"""
        if self.current_interface:
            return self.current_interface.get_message_history()
        return []
    
    def get_messages_dictionary(self):
        """Get current messages as dictionary"""
        if self.current_interface:
            return self.current_interface.get_messages_dictionary()
        return {}
    
    def switch_interface(self, new_interface_type: str) -> bool:
        """Switch to a different interface type"""
        try:
            # Stop current interface
            if self.current_interface:
                self.stop_monitoring()
                self.disconnect()
            
            # Update configuration
            self.interface_type = new_interface_type
            self.config.can_config.interface = new_interface_type
            
            # Initialize new interface
            result = self.initialize_interface()
            if not result:
                self._notify_connection_change(False)
            return result
            
        except Exception as e:
            self.logger.error(f"Error switching interface: {e}")
            self._notify_connection_change(False)
            return False
    
    def get_available_interfaces(self) -> list:
        """Get list of available interface types"""
        return CANInterfaceFactory.get_available_interfaces()
    
    def is_connected(self) -> bool:
        """Check if interface is connected"""
        return self.current_interface and self.current_interface.is_connected
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self.current_interface and self.current_interface.is_monitoring
