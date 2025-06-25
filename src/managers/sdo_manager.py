import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from interfaces import CANMessage

@dataclass
class SDORequest:
    """SDO request tracking information"""
    node_id: int
    index: int
    sub_index: int
    value: int
    timestamp: datetime
    timeout_ms: int = 1000
    callback: Optional[Callable] = None
    completed: bool = False
    success: bool = False
    error_code: Optional[int] = None
    error_message: str = ""

class SDOManager:
    """Manages SDO expedited transfers with response tracking"""
    
    def __init__(self, interface_manager, logger):
        self.interface_manager = interface_manager
        self.logger = logger
        self.pending_requests: Dict[str, SDORequest] = {}  # Key: "node_id_index_subindex"
        self.response_thread = None
        self.running = False
        
        # SDO Abort codes
        self.abort_codes = {
            0x05030000: "Toggle bit not alternated",
            0x05040000: "SDO protocol timed out",
            0x05040001: "Client/server command specifier not valid or unknown",
            0x05040002: "Invalid block size",
            0x05040003: "Invalid sequence number",
            0x05040004: "CRC error",
            0x05040005: "Out of memory",
            0x06010000: "Unsupported access to an object",
            0x06010001: "Attempt to read a write only object",
            0x06010002: "Attempt to write a read only object",
            0x06020000: "Object does not exist in the object dictionary",
            0x06040041: "Object cannot be mapped to the PDO",
            0x06040042: "The number and length of the objects to be mapped would exceed PDO length",
            0x06040043: "General parameter incompatibility reason",
            0x06040047: "General internal incompatibility in the device",
            0x06060000: "Access failed due to a hardware error",
            0x06070010: "Data type does not match, length of service parameter does not match",
            0x06070012: "Data type does not match, length of service parameter too high",
            0x06070013: "Data type does not match, length of service parameter too low",
            0x06090011: "Sub-index does not exist",
            0x06090030: "Invalid value for parameter",
            0x06090031: "Value of parameter written too high",
            0x06090032: "Value of parameter written too low",
            0x06090036: "Maximum value is less than minimum value",
            0x060A0023: "Resource not available",
            0x08000000: "General error",
            0x08000020: "Data cannot be transferred or stored to the application",
            0x08000021: "Data cannot be transferred or stored to the application because of local control",
            0x08000022: "Data cannot be transferred or stored to the application because of the present device state",
            0x08000023: "Object dictionary dynamic generation fails or no object dictionary is present"
        }
    
    def start(self):
        """Start the SDO response monitoring"""
        if not self.running:
            self.running = True
            self.response_thread = threading.Thread(target=self._response_monitor_thread)
            self.response_thread.daemon = True
            self.response_thread.start()
            
            # Register for CAN messages
            if self.interface_manager:
                self.interface_manager.add_message_callback(self._on_can_message)
    
    def stop(self):
        """Stop the SDO response monitoring"""
        self.running = False
        if self.interface_manager:
            self.interface_manager.remove_message_callback(self._on_can_message)
    
    def send_sdo_expedited_write(self, node_id: int, index: int, sub_index: int, 
                                value: int, data_size: int, callback: Callable = None,
                                timeout_ms: int = 1000) -> bool:
        """Send SDO expedited write with response tracking"""
        try:
            # Create request tracking
            request_key = f"{node_id}_{index:04X}_{sub_index:02X}"
            request = SDORequest(
                node_id=node_id,
                index=index,
                sub_index=sub_index,
                value=value,
                timestamp=datetime.now(),
                timeout_ms=timeout_ms,
                callback=callback
            )
            
            # Store pending request
            self.pending_requests[request_key] = request
            
            # Send SDO using interface manager
            success = self.interface_manager.send_sdo_expedited(
                node_id=node_id,
                index=index,
                sub_index=sub_index,
                value=value,
                data_size=data_size
            )
            
            if success:
                self.logger.info(f"SDO expedited write sent - Node: {node_id}, Index: 0x{index:04X}:{sub_index:02X}, Value: {value}")
            else:
                # Remove from pending if send failed
                self.pending_requests.pop(request_key, None)
                self.logger.error(f"Failed to send SDO expedited write - Node: {node_id}, Index: 0x{index:04X}:{sub_index:02X}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending SDO expedited write: {e}")
            return False
    
    def send_sdo_expedited_read(self, node_id: int, index: int, sub_index: int, 
                                callback: Callable = None, timeout_ms: int = 1000) -> bool:
        """Send SDO expedited read (upload) with response tracking"""
        try:
            # Create request tracking
            request_key = f"{node_id}_{index:04X}_{sub_index:02X}_READ"
            request = SDORequest(
                node_id=node_id,
                index=index,
                sub_index=sub_index,
                value=0,  # Not applicable for read
                timestamp=datetime.now(),
                timeout_ms=timeout_ms,
                callback=callback
            )
            
            # Store pending request
            self.pending_requests[request_key] = request
            
            # Send SDO read using interface manager
            success = self.interface_manager.send_sdo_read(
                node_id=node_id,
                index=index,
                sub_index=sub_index
            )
            
            if success:
                self.logger.info(f"SDO expedited read sent - Node: {node_id}, Index: 0x{index:04X}:{sub_index:02X}")
            else:
                # Remove from pending if send failed
                self.pending_requests.pop(request_key, None)
                self.logger.error(f"Failed to send SDO expedited read - Node: {node_id}, Index: 0x{index:04X}:{sub_index:02X}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending SDO expedited read: {e}")
            return False
    
    def _on_can_message(self, message: CANMessage):
        """Process incoming CAN messages for SDO responses"""
        try:
            # Check if this is an SDO response (COB-ID 0x580 + node_id)
            if 0x580 <= message.cob_id <= 0x5FF and len(message.data) >= 8:
                node_id = message.cob_id - 0x580
                self._process_sdo_response(node_id, message.data)
                
        except Exception as e:
            self.logger.error(f"Error processing CAN message for SDO: {e}")
    
    def _process_sdo_response(self, node_id: int, data: list):
        """Process SDO response message"""
        try:
            if len(data) < 8:
                return
            
            # Parse SDO response
            cs = (data[0] >> 5) & 0x07  # Command specifier
            index = (data[2] << 8) | data[1]  # Index (little endian)
            sub_index = data[3]  # Sub-index
            
            # Create request keys for both write and read
            write_key = f"{node_id}_{index:04X}_{sub_index:02X}"
            read_key = f"{node_id}_{index:04X}_{sub_index:02X}_READ"
            
            # Find matching pending request (prioritize read then write)
            request = None
            request_key = None
            
            if read_key in self.pending_requests:
                request = self.pending_requests[read_key]
                request_key = read_key
            elif write_key in self.pending_requests:
                request = self.pending_requests[write_key]
                request_key = write_key
            
            if not request:
                return
            
            if cs == 2:  # SDO upload response (read success)
                # Extract data from upload response
                e = (data[0] >> 1) & 0x01  # Expedited transfer
                s = data[0] & 0x01  # Size indicated
                n = (data[0] >> 2) & 0x03  # Number of bytes without data
                
                if e == 1:  # Expedited transfer
                    # Extract value based on size
                    if s == 1:  # Size indicated
                        data_size = 4 - n
                        value_bytes = data[4:4+data_size]
                        value = self._bytes_to_value(value_bytes)
                    else:
                        # Use all 4 data bytes
                        value_bytes = data[4:8]
                        value = self._bytes_to_value(value_bytes)
                    
                    self._handle_sdo_read_success(request, value)
                else:
                    # Segmented transfer not implemented yet
                    self._handle_sdo_abort(request, 0x08000000)  # General error
                    
            elif cs == 3:  # SDO download response (write success)
                self._handle_sdo_success(request)
            elif cs == 4:  # SDO abort
                abort_code = (data[7] << 24) | (data[6] << 16) | (data[5] << 8) | data[4]
                self._handle_sdo_abort(request, abort_code)
            
            # Remove completed request
            if request_key:
                self.pending_requests.pop(request_key, None)
            
        except Exception as e:
            self.logger.error(f"Error processing SDO response: {e}")
    
    def _bytes_to_value(self, bytes_data: list) -> int:
        """Convert bytes to integer value (little endian)"""
        value = 0
        for i, byte in enumerate(bytes_data):
            value |= (byte << (i * 8))
        return value
    
    def _handle_sdo_success(self, request: SDORequest):
        """Handle successful SDO response"""
        request.completed = True
        request.success = True
        
        self.logger.info(f"SDO write successful - Node: {request.node_id}, Index: 0x{request.index:04X}:{request.sub_index:02X}")
        
        # Call callback if provided
        if request.callback:
            try:
                request.callback(True, "Success", None)
            except Exception as e:
                self.logger.error(f"Error in SDO success callback: {e}")
    
    def _handle_sdo_abort(self, request: SDORequest, abort_code: int):
        """Handle SDO abort response"""
        request.completed = True
        request.success = False
        request.error_code = abort_code
        request.error_message = self.abort_codes.get(abort_code, f"Unknown abort code: 0x{abort_code:08X}")
        
        self.logger.error(f"SDO write aborted - Node: {request.node_id}, Index: 0x{request.index:04X}:{request.sub_index:02X}, "
                         f"Code: 0x{abort_code:08X}, Message: {request.error_message}")
        
        # Call callback if provided
        if request.callback:
            try:
                request.callback(False, request.error_message, abort_code)
            except Exception as e:
                self.logger.error(f"Error in SDO abort callback: {e}")
    
    def _handle_sdo_read_success(self, request: SDORequest, value: int):
        """Handle successful SDO read response"""
        request.completed = True
        request.success = True
        request.value = value  # Store the read value
        
        self.logger.info(f"SDO read successful - Node: {request.node_id}, Index: 0x{request.index:04X}:{request.sub_index:02X}, Value: {value}")
        
        # Call callback if provided
        if request.callback:
            try:
                request.callback(True, "Success", value)
            except Exception as e:
                self.logger.error(f"Error in SDO read success callback: {e}")
    
    def _response_monitor_thread(self):
        """Monitor thread for SDO timeouts"""
        while self.running:
            try:
                current_time = datetime.now()
                expired_requests = []
                
                # Check for expired requests
                for key, request in self.pending_requests.items():
                    if not request.completed:
                        elapsed_ms = (current_time - request.timestamp).total_seconds() * 1000
                        if elapsed_ms > request.timeout_ms:
                            expired_requests.append(key)
                
                # Handle timeouts
                for key in expired_requests:
                    request = self.pending_requests.pop(key, None)
                    if request:
                        self._handle_sdo_timeout(request)
                
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                self.logger.error(f"Error in SDO response monitor thread: {e}")
    
    def _handle_sdo_timeout(self, request: SDORequest):
        """Handle SDO timeout"""
        request.completed = True
        request.success = False
        request.error_message = f"SDO timeout after {request.timeout_ms}ms"
        
        self.logger.warning(f"SDO write timeout - Node: {request.node_id}, Index: 0x{request.index:04X}:{request.sub_index:02X}")
        
        # Call callback if provided
        if request.callback:
            try:
                request.callback(False, request.error_message, None)
            except Exception as e:
                self.logger.error(f"Error in SDO timeout callback: {e}")
    
    def get_pending_requests(self) -> Dict[str, SDORequest]:
        """Get current pending requests"""
        return self.pending_requests.copy()
    
    def clear_pending_requests(self):
        """Clear all pending requests"""
        self.pending_requests.clear()
