import serial
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_interface import BaseCANInterface, CANMessage

class USBSerialCANInterface(BaseCANInterface):
    """CAN interface for USB-Serial converters"""
    
    def __init__(self, com_port: str = "COM1", baudrate: int = 115200):
        super().__init__()
        self.com_port = com_port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.communication_thread: Optional[threading.Thread] = None
        self.last_valid_messages: Dict[str, List[int]] = {}
        self._lock = threading.Lock()
        
    def connect(self, com_port: str = None, baudrate: int = None) -> bool:
        """Connect to USB-Serial CAN converter"""
        try:
            if com_port:
                self.com_port = com_port
            if baudrate:
                self.baudrate = baudrate
                
            self.ser = serial.Serial(self.com_port, self.baudrate)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"ERROR: Error connecting to {self.com_port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from USB-Serial CAN converter"""
        self.stop_monitoring()
        self.is_connected = False
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def start_monitoring(self) -> bool:
        """Start monitoring CAN messages"""
        if not self.is_connected or not self.ser:
            print("ERROR: Cannot start monitoring - not connected")
            return False
        
        # Clear any pending data in serial buffer and message history
        self._clear_buffers()
            
        self.is_monitoring = True
        self.communication_thread = threading.Thread(target=self._communication_loop)
        self.communication_thread.daemon = True
        self.communication_thread.start()
        return True
    
    def _clear_buffers(self):
        """Clear serial buffer and message history before starting monitoring"""
        try:
            # Clear serial input buffer
            if self.ser and self.ser.is_open:
                self.ser.reset_input_buffer()
                print("DEBUG: Serial input buffer cleared")
            
            # Clear internal message storage
            with self._lock:
                self.last_valid_messages.clear()
                self.message_stack.clear()
                self.message_history.clear()
                print("DEBUG: Message buffers cleared")
                
        except Exception as e:
            print(f"ERROR: Error clearing buffers: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring CAN messages"""
        self.is_monitoring = False
        if self.communication_thread and self.communication_thread.is_alive():
            self.communication_thread.join(timeout=1.0)
    
    def _communication_loop(self):
        """Main communication loop (adapted from original analyzer.py)"""
        buffer = []  # Almacenará los bytes del mensaje actual
        reading_message = False  # Indicador para saber si estamos en un mensaje
        message_start_time = 0  # Para llevar el tiempo desde que se empezó a leer un mensaje
        timeout = 0.1  # 100ms de timeout para considerar un mensaje inválido
        
        try:
            while self.is_monitoring:
                # Leer un byte desde el puerto serial
                if self.ser.in_waiting > 0:
                    byte = self.ser.read(1)
                    byte_value = int.from_bytes(byte, byteorder='big')

                    # Si encontramos el encabezado AA, iniciamos la captura del mensaje
                    if byte_value == 0xAA and not reading_message:
                        reading_message = True
                        message_start_time = time.time()
                        buffer = [byte_value]  # Reiniciar el buffer e incluir el encabezado
                    elif reading_message:
                        # Verificar timeout
                        if (time.time() - message_start_time) > timeout:
                            reading_message = False
                            continue
                            
                        buffer.append(byte_value)
                        
                        # Si encontramos el código de finalización 55, procesamos el mensaje
                        if byte_value == 0x55:
                            self._process_message(buffer)
                            reading_message = False  # Resetear el indicador para el siguiente mensaje
                
                # Pequeña pausa para no saturar la CPU
                else:
                    time.sleep(0.001)

        except Exception as e:
            if self.is_monitoring:
                print(f"ERROR: Error in communication loop: {e}")
    
    def _process_message(self, buffer: List[int]):
        """Process complete message (adapted from original analyzer.py)"""
        # Procesar el mensaje completo
        if len(buffer) < 5:
            return
        
        try:
            header = buffer[0]
            length_info = buffer[1]
            frame_id = (buffer[3] << 8) | buffer[2]
            data_length = length_info & 0x0F
            
            # Verificar que el buffer tiene suficientes datos
            if len(buffer) < (4 + data_length + 1):  # header + length + id(2) + data + end
                return
                
            data = buffer[4:4 + data_length]
            end_code = buffer[-1]
            
            frame_id_str = f'{frame_id&0xFFF:03X}'
            
            # Solo actualizar si el mensaje es válido y completo
            if end_code == 0x55 and len(data) == data_length:
                with self._lock:
                    self.last_valid_messages[frame_id_str] = data
                    self.message_stack = self.last_valid_messages.copy()
                
                # Create CANMessage object for the interface
                can_message = self._create_can_message(frame_id, data)
                
                # Add to history
                self.message_history.append(can_message)
                if len(self.message_history) > 1000:  # Keep only last 1000 messages
                    self.message_history.pop(0)
                
                # Notify callbacks
                self._notify_callbacks(can_message)
            else:
                # Si el mensaje no es válido, mantener el último valor válido
                if frame_id_str in self.last_valid_messages:
                    with self._lock:
                        self.message_stack[frame_id_str] = self.last_valid_messages[frame_id_str]
                    
        except Exception as e:
            print(f"ERROR: Error processing message: {e}")
            # En caso de error, mantener los últimos valores válidos
            with self._lock:
                self.message_stack = self.last_valid_messages.copy()
    
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
        """Send data through USB-Serial interface (adapted from original analyzer.py)"""
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

            # Get node ID (default to 1)
            node_id = send_data.get('node_id', 1)
            if isinstance(node_id, str):
                node_id = int(node_id)

            is_read = send_data.get('is_read', False)

            # Comando CANopen para escritura expedited con tamaño
            command_map = {
                1: 0x2F,
                2: 0x2B,
                3: 0x27,
                4: 0x23
            }
            command = 0x40 if is_read else command_map[size]

            # Datos en little endian con padding hasta 4 bytes
            data_bytes = [(value >> (8 * i)) & 0xFF for i in range(size)] if not is_read else [0] * 4
            data_bytes += [0x00] * (4 - len(data_bytes))

            # Calculate SDO COB-ID: 0x600 + node_id for SDO Tx
            sdo_cob_id = 0x600 + node_id
            frame_id_lsb = sdo_cob_id & 0xFF
            frame_id_msb = (sdo_cob_id >> 8) & 0xFF

            # Index en little endian
            index_lsb = index & 0xFF
            index_msb = (index >> 8) & 0xFF

            # Payload CAN de 8 bytes
            sdo_payload = [command, index_lsb, index_msb, subindex] + data_bytes

            # Armar cadena hexadecimal completa
            header = "AA"
            size_hex = f"C{len(sdo_payload)}"
            end = "55"
            full_hex = header + size_hex + f"{frame_id_lsb:02X}{frame_id_msb:02X}" + ''.join(f"{x:02X}" for x in sdo_payload) + end

            # Enviar como bytes
            byte_array = bytes.fromhex(full_hex)
            self.ser.write(byte_array)

            # print(f"""
            # SDO Message sent:
            # Header: 0xAA (Fixed start)
            # Type: 0x{size_hex}
            # Frame ID: {frame_id_msb:02X} {frame_id_lsb:02X} (COB-ID: 0x{sdo_cob_id:03X})
            # Node ID: {node_id}
            # Command: 0x{command:02X}
            # Index: 0x{index:04X}
            # Subindex: 0x{subindex:02X}
            # Data: {' '.join(f'0x{x:02X}' for x in data_bytes)}
            # End: 0x55
            # Complete frame: {' '.join(f'0x{x:02X}' for x in byte_array)}
            # """)

            return True

        except Exception as e:
            print(f"ERROR: Error sending data: {e}")
            return False

    def send_can_frame(self, frame_id: int, data: List[int], is_extended: bool = False, is_remote: bool = False) -> bool:
        if not self.is_connected or not self.ser:
            print("ERROR: Not connected to USB-Serial interface")
            return False

        try:
            # Header
            header = 0xAA

            # Control byte:
            control = 0xC0  # bit7=1, bit6=1 (0xC0)
            if is_extended:
                control |= 0x20  # bit5=1 for extended frame
            if is_remote:
                control |= 0x10  # bit4=1 for remote frame
            control |= len(data) & 0x0F  # last 4 bits: length

            frame = [header, control]

            # Frame ID (little endian)
            if is_extended:
                # 4 bytes
                frame += [
                    (frame_id >> 0) & 0xFF,
                    (frame_id >> 8) & 0xFF,
                    (frame_id >> 16) & 0xFF,
                    (frame_id >> 24) & 0xFF,
                ]
            else:
                # 2 bytes
                frame += [
                    (frame_id >> 0) & 0xFF,
                    (frame_id >> 8) & 0xFF,
                ]

            # Data bytes
            frame += data

            # End code
            frame.append(0x55)

            # Enviar por serial
            self.ser.write(bytes(frame))
            # print(f"DEBUG: Sent frame: {[f'0x{x:02X}' for x in frame]}")
            return True

        except Exception as e:
            print(f"ERROR: Error sending CAN frame: {e}")
            return False

