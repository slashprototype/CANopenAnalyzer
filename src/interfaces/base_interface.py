from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CANMessage:
    """Represents a CAN message with CANopen information"""
    timestamp: datetime
    cob_id: int
    node_id: int
    function_code: int
    data: List[int]
    message_type: str
    length: int
    raw_data: bytes = None

class BaseCANInterface(ABC):
    """Base interface for CAN communication implementations"""
    
    def __init__(self):
        self.is_connected = False
        self.is_monitoring = False
        self.message_callbacks: List[Callable] = []
        self.message_history: List[CANMessage] = []
        self.message_stack: Dict[str, List[int]] = {}
        
    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """Connect to the CAN interface"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the CAN interface"""
        pass
    
    @abstractmethod
    def start_monitoring(self) -> bool:
        """Start monitoring CAN messages"""
        pass
    
    @abstractmethod
    def stop_monitoring(self):
        """Stop monitoring CAN messages"""
        pass
    
    @abstractmethod
    def send_data(self, send_data: Dict[str, Any]) -> bool:
        """Send data through the CAN interface"""
        pass
    
    def add_message_callback(self, callback: Callable):
        """Add callback for new messages"""
        self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable):
        """Remove message callback"""
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    def get_message_history(self) -> List[CANMessage]:
        """Get copy of message history"""
        return self.message_history.copy()
    
    def get_messages_dictionary(self) -> Dict[str, List[int]]:
        """Get current message stack as dictionary"""
        return self.message_stack.copy()
    
    def _notify_callbacks(self, message: CANMessage):
        """Notify all registered callbacks of new message"""
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in message callback: {e}")
