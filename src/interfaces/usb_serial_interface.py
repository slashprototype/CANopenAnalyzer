import serial
import threading
import time
import os
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import deque

from .base_interface import BaseCANInterface, CANMessage

class USBSerialCANInterface(BaseCANInterface):
    """CAN interface for USB-Serial converters with high-performance optimization"""
    
    def __init__(self, com_port: str = "COM1", baudrate: int = 115200):
        super().__init__()
        self.com_port = com_port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.communication_thread: Optional[threading.Thread] = None
        
        # NUEVO: Buffer centralizado de alto rendimiento
        self._message_buffer = deque(maxlen=50000)  # Buffer grande para alta velocidad
        self._buffer_lock = threading.RLock()  # RLock para mejor rendimiento
        self._latest_messages = {}  # {cob_id: latest_message} para acceso rápido
        self._statistics = {
            'total_received': 0,
            'messages_per_second': 0,
            'buffer_size': 0,
            'last_update': time.time()
        }
        
        # Optimización de callbacks - solo para eventos críticos
        self._critical_callbacks = []  # Solo para eventos importantes
        self._callback_lock = threading.Lock()
        
        # Variables originales optimizadas
        self.last_valid_messages: Dict[str, List[int]] = {}
        self._lock = threading.Lock()
        
        # High-performance buffers
        self.read_buffer = bytearray()
        self.message_queue = deque(maxlen=10000)
        
        # Performance optimization settings
        self.bulk_read_size = 8192  # AUMENTADO: chunks más grandes
        self.high_priority_mode = True
        self.cpu_affinity = None
        
        # NUEVO: Control de flujo
        self._processing_enabled = True
        self._stats_counter = 0
    
    def connect(self, com_port: str = None, baudrate: int = None) -> bool:
        """Connect to USB-Serial CAN converter with optimized settings"""
        try:
            if com_port:
                self.com_port = com_port
            if baudrate:
                self.baudrate = baudrate
                
            # Configure serial port for high performance
            self.ser = serial.Serial(
                port=self.com_port,
                baudrate=self.baudrate,
                timeout=0.001,  # Very short timeout for non-blocking reads
                write_timeout=0.1,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )
            
            # Configure buffer sizes
            if hasattr(self.ser, 'set_buffer_size'):
                self.ser.set_buffer_size(rx_size=16384, tx_size=16384)
                
            self.is_connected = True
            return True
        except Exception as e:
            print(f"ERROR: Error connecting to {self.com_port}: {e}")
            return False
    
    def _set_high_priority(self):
        """Set high CPU priority and affinity for the communication thread"""
        try:
            if self.high_priority_mode:
                # Get current process
                process = psutil.Process(os.getpid())
                
                # Set process to high priority
                if os.name == 'nt':  # Windows
                    process.nice(psutil.HIGH_PRIORITY_CLASS)
                else:  # Linux/Unix
                    process.nice(-10)
                
                # Set CPU affinity to last core (usually less busy)
                if self.cpu_affinity is None:
                    cpu_count = psutil.cpu_count()
                    self.cpu_affinity = [cpu_count - 1] if cpu_count > 1 else [0]
                
                process.cpu_affinity(self.cpu_affinity)
                print(f"DEBUG: Set high priority and CPU affinity to cores: {self.cpu_affinity}")
                
        except Exception as e:
            print(f"WARNING: Could not set high priority: {e}")
    
    def start_monitoring(self) -> bool:
        """Start high-performance monitoring with centralized buffer"""
        if not self.is_connected or not self.ser:
            print("ERROR: Cannot start monitoring - not connected")
            return False
        
        self._clear_buffers()
        self._processing_enabled = True
        self.is_monitoring = True
        
        # Start optimized communication thread
        self.communication_thread = threading.Thread(target=self._optimized_communication_loop)
        self.communication_thread.daemon = True
        self.communication_thread.start()
        
        return True
    
    def _clear_buffers(self):
        """Clear all buffers before starting monitoring"""
        try:
            # Clear serial input buffer
            if self.ser and self.ser.is_open:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            
            # Clear internal buffers
            with self._buffer_lock:
                self._message_buffer.clear()
                self._latest_messages.clear()
                
            with self._lock:
                self.last_valid_messages.clear()
                self.message_stack.clear()
                self.message_history.clear()
                self.read_buffer.clear()
                self.message_queue.clear()
            
            # Reset statistics
            self._statistics = {
                'total_received': 0,
                'messages_per_second': 0,
                'buffer_size': 0,
                'last_update': time.time()
            }
                
        except Exception as e:
            print(f"ERROR: Error clearing buffers: {e}")
    
    def _optimized_communication_loop(self):
        """Highly optimized communication loop with centralized buffering"""
        self._set_high_priority()
        
        buffer = bytearray()
        message_batch = []
        last_stats_update = time.time()
        messages_this_second = 0
        
        try:
            while self.is_monitoring and self._processing_enabled:
                current_time = time.time()
                
                # Read data in larger chunks
                if self.ser.in_waiting > 0:
                    chunk_size = min(self.bulk_read_size, self.ser.in_waiting)
                    new_data = self.ser.read(chunk_size)
                    
                    if new_data:
                        buffer.extend(new_data)
                        self._extract_and_buffer_messages(buffer, message_batch)
                
                # Process accumulated messages in batch
                if message_batch:
                    self._process_message_batch_optimized(message_batch)
                    messages_this_second += len(message_batch)
                    message_batch.clear()
                
                # Update statistics every second
                if current_time - last_stats_update >= 1.0:
                    with self._buffer_lock:
                        self._statistics.update({
                            'messages_per_second': messages_this_second,
                            'buffer_size': len(self._message_buffer),
                            'last_update': current_time
                        })
                    messages_this_second = 0
                    last_stats_update = current_time
                
                # Micro sleep for CPU efficiency
                time.sleep(0.0001)  # 0.1ms
                
        except Exception as e:
            if self.is_monitoring:
                print(f"ERROR: Error in optimized communication loop: {e}")
    
    def _extract_and_buffer_messages(self, buffer: bytearray, message_batch: list):
        """Extract messages and add to batch for processing"""
        while len(buffer) >= 5:
            start_idx = buffer.find(0xAA)
            if start_idx == -1:
                buffer.clear()
                break
                
            if start_idx > 0:
                del buffer[:start_idx]
                continue
                
            if len(buffer) < 2:
                break
                
            length_info = buffer[1]
            data_length = length_info & 0x0F
            expected_length = 4 + data_length + 1
            
            if len(buffer) < expected_length:
                break
                
            message_data = list(buffer[:expected_length])
            
            if message_data[-1] == 0x55:
                message_batch.append(message_data)
            
            del buffer[:expected_length]
    
    def _process_message_batch_optimized(self, message_batch):
        """Process message batch with centralized buffering"""
        processed_messages = []
        current_time = time.time()
        
        # Process all messages in batch
        for message_data in message_batch:
            if len(message_data) < 5:
                continue
                
            try:
                header = message_data[0]
                length_info = message_data[1]
                frame_id = (message_data[3] << 8) | message_data[2]
                data_length = length_info & 0x0F
                
                if len(message_data) < (4 + data_length + 1):
                    continue
                    
                data = message_data[4:4 + data_length]
                end_code = message_data[-1]
                
                if end_code == 0x55 and len(data) == data_length:
                    can_message = self._create_can_message(frame_id, data)
                    can_message.timestamp = datetime.fromtimestamp(current_time)  # Timestamp consistente
                    processed_messages.append(can_message)
                    
            except Exception as e:
                continue  # Skip malformed messages
        
        # Batch update of centralized buffer
        if processed_messages:
            with self._buffer_lock:
                for msg in processed_messages:
                    # Add to main buffer
                    self._message_buffer.append(msg)
                    
                    # Update latest message cache for quick access
                    cob_id_key = f"{msg.cob_id:03X}"
                    self._latest_messages[cob_id_key] = msg
                    
                    # Update statistics
                    self._statistics['total_received'] += 1
            
            # Update legacy structures for compatibility (minimal)
            with self._lock:
                for msg in processed_messages:
                    frame_id_str = f'{msg.cob_id:03X}'
                    self.last_valid_messages[frame_id_str] = msg.data
                    self.message_stack[frame_id_str] = msg.data
                    
                    # Keep minimal history
                    self.message_history.append(msg)
                    if len(self.message_history) > 1000:  # REDUCIDO para mejor performance
                        del self.message_history[:500]
            
            # OPTIMIZADO: Solo callbacks críticos
            self._notify_critical_callbacks_batch(processed_messages)
    
    def _notify_critical_callbacks_batch(self, messages):
        """Notify only critical callbacks with batch of messages"""
        if not self._critical_callbacks:
            return
            
        with self._callback_lock:
            for callback in self._critical_callbacks:
                try:
                    # Pass batch of messages instead of individual calls
                    if hasattr(callback, 'process_message_batch'):
                        callback.process_message_batch(messages)
                    else:
                        # Fallback to individual messages for compatibility
                        for msg in messages[-5:]:  # Only last 5 messages
                            callback(msg)
                except Exception as e:
                    print(f"ERROR: Error in critical callback: {e}")
    
    # NUEVO: Métodos de acceso optimizados para otros módulos
    def get_latest_messages(self, max_count: int = 1000) -> List[CANMessage]:
        """Get latest messages from buffer efficiently"""
        with self._buffer_lock:
            if max_count >= len(self._message_buffer):
                return list(self._message_buffer)
            else:
                return list(self._message_buffer)[-max_count:]
    
    def get_latest_by_cob_id(self, cob_id: int) -> Optional[CANMessage]:
        """Get latest message for specific COB-ID"""
        cob_id_key = f"{cob_id:03X}"
        with self._buffer_lock:
            return self._latest_messages.get(cob_id_key)
    
    def get_messages_since(self, timestamp: float) -> List[CANMessage]:
        """Get messages received since timestamp"""
        with self._buffer_lock:
            return [msg for msg in self._message_buffer 
                   if msg.timestamp.timestamp() > timestamp]
    
    def get_statistics(self) -> Dict:
        """Get interface statistics"""
        with self._buffer_lock:
            return self._statistics.copy()
    
    def add_critical_callback(self, callback):
        """Add callback for critical events only"""
        with self._callback_lock:
            if callback not in self._critical_callbacks:
                self._critical_callbacks.append(callback)
    
    def remove_critical_callback(self, callback):
        """Remove critical callback"""
        with self._callback_lock:
            if callback in self._critical_callbacks:
                self._critical_callbacks.remove(callback)
    
    # DEPRECATED: Legacy callback methods - maintain for compatibility but discourage use
    def add_message_callback(self, callback):
        """DEPRECATED: Use add_critical_callback or polling methods instead"""
        print("WARNING: add_message_callback is deprecated. Use polling methods for better performance.")
        self.add_critical_callback(callback)
    
    def remove_message_callback(self, callback):
        """DEPRECATED: Use remove_critical_callback instead"""
        self.remove_critical_callback(callback)
    
    def stop_monitoring(self):
        """Stop monitoring CAN messages"""
        self.is_monitoring = False
        
        # Wait for threads to finish
        if self.communication_thread and self.communication_thread.is_alive():
            self.communication_thread.join(timeout=1.0)
        if hasattr(self, 'processing_thread') and self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
    
    def _process_message(self, buffer: List[int]):
        """Process complete message with optimized performance"""
        if len(buffer) < 5:
            return
        
        try:
            header = buffer[0]
            length_info = buffer[1]
            frame_id = (buffer[3] << 8) | buffer[2]
            data_length = length_info & 0x0F
            
            # Verify buffer has enough data
            if len(buffer) < (4 + data_length + 1):
                return
                
            data = buffer[4:4 + data_length]
            end_code = buffer[-1]
            
            frame_id_str = f'{frame_id&0xFFF:03X}'
            
            # Only update if message is valid and complete
            if end_code == 0x55 and len(data) == data_length:
                # Use faster locking strategy
                with self._lock:
                    self.last_valid_messages[frame_id_str] = data
                    self.message_stack[frame_id_str] = data
                
                # Create CANMessage object
                can_message = self._create_can_message(frame_id, data)
                # print(f"DEBUG: Processed message: {can_message}")
                
                # Add to history with size limit
                self.message_history.append(can_message)
                if len(self.message_history) > 5000:  # Increased buffer size
                    # Remove older messages in chunks for better performance
                    del self.message_history[:1000]
                
                # Notify callbacks
                self._notify_callbacks(can_message)
                    
        except Exception as e:
            print(f"ERROR: Error processing message: {e}")
            # Maintain last valid messages on error
            with self._lock:
                if frame_id_str in self.last_valid_messages:
                    self.message_stack[frame_id_str] = self.last_valid_messages[frame_id_str]
    
    def _create_can_message(self, frame_id: int, data: List[int]) -> CANMessage:
        """Create CANMessage object from frame data"""
        cob_id = frame_id & 0x7FF
        node_id = cob_id & 0x7F
        function_code = (cob_id >> 7) & 0xF

        # Determine message type based on CANopen COB-ID ranges
        message_type = "Unknown"
        # TPDOs: 0x180, 0x280, 0x380, 0x480 (TPDO1-4)
        if 0x180 <= cob_id < 0x200:
            message_type = "TPDO1"
        elif 0x280 <= cob_id < 0x300:
            message_type = "TPDO2"
        elif 0x380 <= cob_id < 0x400:
            message_type = "TPDO3"
        elif 0x480 <= cob_id < 0x500:
            message_type = "TPDO4"
        # RPDOs: 0x200, 0x300, 0x400, 0x500 (RPDO1-4)
        elif 0x200 <= cob_id < 0x280:
            message_type = "RPDO1"
        elif 0x300 <= cob_id < 0x380:
            message_type = "RPDO2"
        elif 0x400 <= cob_id < 0x480:
            message_type = "RPDO3"
        elif 0x500 <= cob_id < 0x580:
            message_type = "RPDO4"
        # SDOs: 0x600 (Rx), 0x580 (Tx)
        elif 0x600 <= cob_id < 0x700:
            message_type = "SDO Rx"
        elif 0x580 <= cob_id < 0x600:
            message_type = "SDO Tx"
        # NMT: 0x000
        elif cob_id == 0x000:
            message_type = "NMT"
        # Emergency: 0x080
        elif 0x080 <= cob_id < 0x100:
            message_type = "Emergency"
        # Heartbeat: 0x700
        elif 0x700 <= cob_id < 0x780:
            message_type = "Heartbeat"

        return CANMessage(
            timestamp=datetime.now(),
            cob_id=cob_id,
            node_id=node_id,
            function_code=function_code,
            data=data,
            message_type=message_type,
            length=len(data),
            raw_data=bytes(data)
        )
    
    def send_data(self, send_data: Dict[str, Any]) -> bool:
        """Send data through USB-Serial interface with optimized performance"""
        if not self.is_connected or not self.ser:
            print("ERROR: Not connected to USB-Serial interface")
            return False
            
        try:
            value = send_data.get('value', 0)
            if isinstance(value, str) and value.startswith('0x'):
                value = int(value, 16)

            size = int(send_data.get('size', 8) / 8)
            if size not in [1, 2, 3, 4]:
                raise ValueError(f"Invalid size parameter: {size}. Must be 1, 2, 3 or 4 bytes.")

            index = send_data.get('index', 0)
            if isinstance(index, str):
                index = int(index.replace('0x', ''), 16)
            else:
                index = int(index)

            subindex = send_data.get('position', send_data.get('subindex', 0))
            if isinstance(subindex, str):
                if subindex.startswith('0x'):
                    subindex = int(subindex, 16)
                else:
                    subindex = int(subindex)

            node_id = send_data.get('node_id', 1)
            if isinstance(node_id, str):
                node_id = int(node_id)

            is_read = send_data.get('is_read', False)

            command_map = {
                1: 0x2F,
                2: 0x2B,
                3: 0x27,
                4: 0x23
            }
            command = 0x40 if is_read else command_map[size]

            data_bytes = [(value >> (8 * i)) & 0xFF for i in range(size)] if not is_read else [0] * 4
            data_bytes += [0x00] * (4 - len(data_bytes))

            sdo_cob_id = 0x600 + node_id
            frame_id_lsb = sdo_cob_id & 0xFF
            frame_id_msb = (sdo_cob_id >> 8) & 0xFF

            index_lsb = index & 0xFF
            index_msb = (index >> 8) & 0xFF

            sdo_payload = [command, index_lsb, index_msb, subindex] + data_bytes

            header = "AA"
            size_hex = f"C{len(sdo_payload)}"
            end = "55"
            full_hex = header + size_hex + f"{frame_id_lsb:02X}{frame_id_msb:02X}" + ''.join(f"{x:02X}" for x in sdo_payload) + end

            # Send as bytes with immediate flush for better timing
            byte_array = bytes.fromhex(full_hex)
            self.ser.write(byte_array)
            self.ser.flush()  # Force immediate transmission

            return True

        except Exception as e:
            print(f"ERROR: Error sending data: {e}")
            return False

    def send_can_frame(self, frame_id: int, data: List[int], is_extended: bool = False, is_remote: bool = False) -> bool:
        """Send CAN frame with optimized performance"""
        if not self.is_connected or not self.ser:
            print("ERROR: Not connected to USB-Serial interface")
            return False

        try:
            # Header
            header = 0xAA
            control = 0xC0
            if is_extended:
                control |= 0x20
            if is_remote:
                control |= 0x10
            control |= len(data) & 0x0F

            frame = [header, control]

            if is_extended:
                frame += [
                    (frame_id >> 0) & 0xFF,
                    (frame_id >> 8) & 0xFF,
                    (frame_id >> 16) & 0xFF,
                    (frame_id >> 24) & 0xFF,
                ]
            else:
                frame += [
                    (frame_id >> 0) & 0xFF,
                    (frame_id >> 8) & 0xFF,
                ]

            frame += data
            frame.append(0x55)

            # Send with immediate flush
            self.ser.write(bytes(frame))
            self.ser.flush()
            return True

        except Exception as e:
            print(f"ERROR: Error sending CAN frame: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from USB-Serial CAN converter"""
        self.stop_monitoring()
        self.is_connected = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.stop_monitoring()
        self.is_connected = False
        if self.ser and self.ser.is_open:
            self.ser.close()

