import can
import canopen
import threading
import asyncio
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CANMessage:
    timestamp: datetime
    cob_id: int
    node_id: int
    function_code: int
    data: bytes
    message_type: str
    length: int

class CANopenAnalyzer:
    def __init__(self, interface: str = "socketcan", channel: str = "can0", bitrate: int = 125000):
        self.interface = interface
        self.channel = channel
        self.bitrate = bitrate
        self.bus: Optional[can.Bus] = None
        self.network: Optional[canopen.Network] = None
        self.is_running = False
        self.message_callbacks: List[Callable] = []
        self.nodes: Dict[int, Any] = {}
        self.message_history: List[CANMessage] = []
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to CAN interface"""
        try:
            self.bus = can.Bus(
                interface=self.interface,
                channel=self.channel,
                bitrate=self.bitrate
            )
            
            self.network = canopen.Network()
            self.network.connect(bus=self.bus)
            
            return True
        except Exception as e:
            print(f"Error connecting to CAN: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from CAN interface"""
        self.is_running = False
        if self.network:
            self.network.disconnect()
        if self.bus:
            self.bus.shutdown()
    
    def start_monitoring(self):
        """Start message monitoring in separate thread"""
        if not self.bus:
            return False
            
        self.is_running = True
        monitor_thread = threading.Thread(target=self._monitor_messages)
        monitor_thread.daemon = True
        monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop message monitoring"""
        self.is_running = False
    
    def _monitor_messages(self):
        """Monitor CAN messages (runs in separate thread)"""
        while self.is_running:
            try:
                message = self.bus.recv(timeout=0.1)
                if message:
                    can_msg = self._parse_message(message)
                    
                    with self.lock:
                        self.message_history.append(can_msg)
                        # Keep only last 1000 messages
                        if len(self.message_history) > 1000:
                            self.message_history.pop(0)
                    
                    # Notify callbacks
                    for callback in self.message_callbacks:
                        try:
                            callback(can_msg)
                        except Exception as e:
                            print(f"Error in message callback: {e}")
                            
            except Exception as e:
                if self.is_running:
                    print(f"Error monitoring messages: {e}")
    
    def _parse_message(self, message: can.Message) -> CANMessage:
        """Parse CAN message to CANopen format"""
        cob_id = message.arbitration_id
        node_id = cob_id & 0x7F
        function_code = (cob_id >> 7) & 0xF
        
        # Determine message type
        message_type = "Unknown"
        if function_code == 0x0:
            message_type = "NMT"
        elif function_code == 0x1:
            message_type = "Emergency"
        elif function_code in [0x3, 0x5, 0x9, 0xD]:
            message_type = f"PDO{function_code//4 + 1}"
        elif function_code in [0xB, 0xC]:
            message_type = "SDO"
        elif function_code == 0xE:
            message_type = "Heartbeat"
        
        return CANMessage(
            timestamp=datetime.now(),
            cob_id=cob_id,
            node_id=node_id,
            function_code=function_code,
            data=message.data,
            message_type=message_type,
            length=message.dlc
        )
    
    def add_message_callback(self, callback: Callable):
        """Add callback for new messages"""
        self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable):
        """Remove message callback"""
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    def get_message_history(self) -> List[CANMessage]:
        """Get copy of message history"""
        with self.lock:
            return self.message_history.copy()
    
    def send_nmt_command(self, node_id: int, command: str) -> bool:
        """Send NMT command to node"""
        try:
            if not self.network:
                return False
                
            node = self.network.add_node(node_id, name=f"Node_{node_id}")
            
            if command == "start":
                node.nmt.state = "OPERATIONAL"
            elif command == "stop":
                node.nmt.state = "STOPPED"
            elif command == "pre_operational":
                node.nmt.state = "PRE-OPERATIONAL"
            elif command == "reset":
                node.nmt.state = "RESET"
                
            return True
        except Exception as e:
            print(f"Error sending NMT command: {e}")
            return False
