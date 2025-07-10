#!/usr/bin/env python3
"""
CAN Message Structure Module

PURPOSE:
This module defines the standard structure for CAN messages used throughout the
CANopen Analyzer system. It provides a consistent interface for message handling,
validation, and conversion between different formats.

KEY FEATURES:
- Standardized CAN message structure
- COB-ID analysis and node ID extraction
- Message type determination based on CANopen protocol
- Data validation and formatting
- Timestamp handling
- Human-readable message representation

This module ensures consistency across all components that handle CAN messages.
"""

from typing import List, Dict, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import time

@dataclass
class CANMessage:
    """
    Standard CAN message structure for CANopen protocol
    """
    timestamp: float
    cob_id: int
    data: List[int]
    msg_type: str
    node_id: Optional[int] = None
    function_code: Optional[int] = None
    msg_index: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing"""
        if self.node_id is None:
            self.node_id = self._extract_node_id()
        if self.function_code is None:
            self.function_code = self._extract_function_code()
    
    @classmethod
    def from_tuple(cls, message_tuple: tuple) -> 'CANMessage':
        """
        Create CANMessage from tuple format
        
        Args:
            message_tuple: (timestamp, cob_id, data, msg_type, msg_index)
            
        Returns:
            CANMessage instance
        """
        if len(message_tuple) >= 5:
            timestamp, cob_id, data, msg_type, msg_index = message_tuple[:5]
        elif len(message_tuple) >= 3:
            timestamp, cob_id, data = message_tuple[:3]
            msg_type = CANMessageType.determine_message_type(cob_id)
            msg_index = None
        else:
            raise ValueError(f"Invalid message tuple format: {message_tuple}")
        
        return cls(
            timestamp=float(timestamp),
            cob_id=int(cob_id),
            data=list(data) if isinstance(data, (list, tuple)) else [data],
            msg_type=str(msg_type),
            msg_index=msg_index
        )
    
    def to_tuple(self) -> tuple:
        """Convert to tuple format"""
        return (self.timestamp, self.cob_id, self.data, self.msg_type, self.msg_index)
    
    def _extract_node_id(self) -> Optional[int]:
        """Extract node ID from COB-ID based on message type"""
        if self.msg_type in ["TPDO1", "TPDO2", "TPDO3", "TPDO4"]:
            return self.cob_id & 0x7F
        elif self.msg_type in ["RPDO1", "RPDO2", "RPDO3", "RPDO4"]:
            return self.cob_id & 0x7F
        elif self.msg_type in ["SDO Tx", "SDO Rx"]:
            return self.cob_id & 0x7F
        elif self.msg_type == "Heartbeat":
            return self.cob_id & 0x7F
        elif self.msg_type == "Emergency":
            return self.cob_id & 0x7F
        return None
    
    def _extract_function_code(self) -> Optional[int]:
        """Extract function code from COB-ID"""
        return (self.cob_id >> 7) & 0x0F
    
    @property
    def age_seconds(self) -> float:
        """Get message age in seconds"""
        return time.time() - self.timestamp
    
    @property
    def data_hex(self) -> str:
        """Get data as hex string"""
        return ' '.join(f'{byte:02X}' for byte in self.data)
    
    @property
    def timestamp_str(self) -> str:
        """Get formatted timestamp string"""
        return datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S.%f')[:-3]
    
    def is_valid(self) -> bool:
        """Validate message structure"""
        try:
            # Check COB-ID range
            if not (0 <= self.cob_id <= 0x7FF):
                return False
            
            # Check data length
            if not (0 <= len(self.data) <= 8):
                return False
            
            # Check data values
            if not all(0 <= byte <= 255 for byte in self.data):
                return False
            
            return True
        except:
            return False
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        return (f"CAN[{self.timestamp_str}] "
                f"COB-ID:0x{self.cob_id:03X} "
                f"Node:{self.node_id or 'N/A'} "
                f"Type:{self.msg_type} "
                f"Data:[{self.data_hex}] "
                f"Age:{self.age_seconds:.3f}s")
    
    def __repr__(self) -> str:
        """Developer string representation"""
        return (f"CANMessage(timestamp={self.timestamp}, "
                f"cob_id=0x{self.cob_id:03X}, "
                f"data={self.data}, "
                f"msg_type='{self.msg_type}', "
                f"node_id={self.node_id})")


class CANMessageType:
    """
    CANopen message type determination and constants
    """
    
    # Message type constants
    TPDO1 = "TPDO1"
    TPDO2 = "TPDO2"
    TPDO3 = "TPDO3"
    TPDO4 = "TPDO4"
    RPDO1 = "RPDO1"
    RPDO2 = "RPDO2"
    RPDO3 = "RPDO3"
    RPDO4 = "RPDO4"
    SDO_TX = "SDO Tx"
    SDO_RX = "SDO Rx"
    NMT = "NMT"
    EMERGENCY = "Emergency"
    HEARTBEAT = "Heartbeat"
    UNKNOWN = "Unknown"
    
    @staticmethod
    def determine_message_type(cob_id: int) -> str:
        """Determine message type from COB-ID"""
        if 0x180 <= cob_id < 0x200:
            return CANMessageType.TPDO1
        elif 0x280 <= cob_id < 0x300:
            return CANMessageType.TPDO2
        elif 0x380 <= cob_id < 0x400:
            return CANMessageType.TPDO3
        elif 0x480 <= cob_id < 0x500:
            return CANMessageType.TPDO4
        elif 0x200 <= cob_id < 0x280:
            return CANMessageType.RPDO1
        elif 0x300 <= cob_id < 0x380:
            return CANMessageType.RPDO2
        elif 0x400 <= cob_id < 0x480:
            return CANMessageType.RPDO3
        elif 0x500 <= cob_id < 0x580:
            return CANMessageType.RPDO4
        elif 0x600 <= cob_id < 0x700:
            return CANMessageType.SDO_RX
        elif 0x580 <= cob_id < 0x600:
            return CANMessageType.SDO_TX
        elif cob_id == 0x000:
            return CANMessageType.NMT
        elif 0x080 <= cob_id < 0x100:
            return CANMessageType.EMERGENCY
        elif 0x700 <= cob_id < 0x780:
            return CANMessageType.HEARTBEAT
        else:
            return CANMessageType.UNKNOWN
    
    @staticmethod
    def get_all_types() -> List[str]:
        """Get list of all message types"""
        return [
            CANMessageType.TPDO1, CANMessageType.TPDO2, CANMessageType.TPDO3, CANMessageType.TPDO4,
            CANMessageType.RPDO1, CANMessageType.RPDO2, CANMessageType.RPDO3, CANMessageType.RPDO4,
            CANMessageType.SDO_TX, CANMessageType.SDO_RX,
            CANMessageType.NMT, CANMessageType.EMERGENCY, CANMessageType.HEARTBEAT,
            CANMessageType.UNKNOWN
        ]
    
    @staticmethod
    def is_pdo(msg_type: str) -> bool:
        """Check if message type is PDO"""
        return msg_type in [
            CANMessageType.TPDO1, CANMessageType.TPDO2, CANMessageType.TPDO3, CANMessageType.TPDO4,
            CANMessageType.RPDO1, CANMessageType.RPDO2, CANMessageType.RPDO3, CANMessageType.RPDO4
        ]
    
    @staticmethod
    def is_sdo(msg_type: str) -> bool:
        """Check if message type is SDO"""
        return msg_type in [CANMessageType.SDO_TX, CANMessageType.SDO_RX]
