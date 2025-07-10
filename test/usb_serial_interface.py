#!/usr/bin/env python3
"""
Ultra High-Performance USB-Serial CAN Interface Test Module

PURPOSE:
This module provides a high-performance interface to capture CAN messages from a USB-Serial
device at ultra-high speeds (2M baud). It handles raw serial communication, message parsing,
buffering, and provides methods for external processors to access messages in batches.
The module is optimized for maximum throughput with process isolation and REALTIME priority.

KEY FEATURES:
- Ultra-high speed serial communication (2M baud)
- Large circular buffers for message storage
- Multi-threaded architecture for parallel processing
- Real-time statistics reporting
- Batch message retrieval for external processors
- Buffer management and cleanup capabilities
- Debug controls for development and troubleshooting

Optimized for 2M baud communication with process isolation
Independent module that uses maximum available resources
"""

import serial
import threading
import time
import os
import sys
import psutil
import signal
from collections import deque
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import struct

class UltraHighSpeedCANInterface:
    """
    Ultra high-performance USB-Serial CAN interface
    Designed for 2M baud with maximum resource utilization
    """
    
    def __init__(self, com_port: str = "COM7", baudrate: int = 2000000, debug: bool = False):
        self.com_port = com_port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        
        # Debug control
        self._debug_enabled = debug
        self._verbose_debug = False  # Extra detailed debugging
        
        # High-performance buffers
        self._message_buffer = deque(maxlen=5000)  # Large buffer for ultra-high speed
        self._raw_buffer = bytearray()
        
        # Message processing tracking - FIXED LOGIC
        self._total_received = 0      # Total messages added to buffer since start
        self._total_cleared = 0       # Total messages cleared from buffer
        
        # Threading and process control
        self._communication_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        self._stats_thread: Optional[threading.Thread] = None
        self._running = False
        self._stopping = False  # Add flag to prevent duplicate stops
        self._disconnected = False  # Add flag to prevent duplicate disconnects
        self._lock = threading.RLock()
        self._buffer_lock = threading.RLock()  # Separate lock for buffer management
        
        # Performance statistics
        self._stats = {
            'total_messages': 0,
            'messages_per_second': 0,
            'bytes_per_second': 0,
            'buffer_utilization': 0.0,
            'last_update': time.time(),
            'start_time': None,
            'errors': 0,
            'max_buffer_size': 0
        }
        
        # Message counting for burst processing
        self._message_count_last_second = 0
        self._bytes_count_last_second = 0
        self._last_stats_time = time.time()
        
        # Ultra-high performance settings
        self.bulk_read_size = 32768  # 32KB chunks for maximum throughput
        self.process_batch_size = 1000  # Process messages in large batches
        
        # Process isolation settings
        self._process = None
        self._high_priority_set = False
    
    def enable_debug(self, enabled: bool = True, verbose: bool = False):
        """Enable or disable debug output"""
        self._debug_enabled = enabled
        self._verbose_debug = verbose
        if enabled:
            self._debug_print(f"🐛 Debug enabled (verbose: {verbose})")
    
    def _debug_print(self, message: str, verbose: bool = False):
        """Print debug message if debugging is enabled"""
        if self._debug_enabled and (not verbose or self._verbose_debug):
            print(f"[DEBUG-INTERFACE] {message}")
    
    def _set_maximum_priority(self):
        """Set maximum process priority and CPU optimization"""
        try:
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Set to highest priority
            if os.name == 'nt':  # Windows
                process.nice(psutil.REALTIME_PRIORITY_CLASS)
                print(f"✓ Set REALTIME priority for PID {os.getpid()}")
            else:  # Linux/Unix
                process.nice(-20)  # Highest priority
                print(f"✓ Set highest priority (-20) for PID {os.getpid()}")
            
            # Set CPU affinity to last cores (usually less busy)
            cpu_count = psutil.cpu_count()
            if cpu_count >= 4:
                # Use last 2 cores for maximum isolation
                affinity = [cpu_count - 2, cpu_count - 1]
            elif cpu_count >= 2:
                affinity = [cpu_count - 1]
            else:
                affinity = [0]
                
            process.cpu_affinity(affinity)
            print(f"✓ Set CPU affinity to cores: {affinity}")
            
            # Set memory priority (Windows)
            if os.name == 'nt':
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Set working set size to prevent paging
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.GetCurrentProcess()
                    
                    # Set minimum and maximum working set (128MB)
                    min_ws = 128 * 1024 * 1024
                    max_ws = 256 * 1024 * 1024
                    kernel32.SetProcessWorkingSetSize(handle, min_ws, max_ws)
                    print(f"✓ Set working set size: {min_ws//1024//1024}MB - {max_ws//1024//1024}MB")
                    
                except Exception as e:
                    print(f"⚠ Could not set memory priority: {e}")
            
            self._high_priority_set = True
            
        except Exception as e:
            print(f"⚠ Could not set maximum priority: {e}")
            self._high_priority_set = False
    
    def _optimize_serial_port(self):
        """Configure serial port for maximum performance"""
        try:
            # Configure serial with ultra-high performance settings
            self.ser = serial.Serial()
            self.ser.port = self.com_port
            self.ser.baudrate = self.baudrate
            
            # Ultra-fast timing settings
            self.ser.timeout = 0.0001  # 0.1ms timeout for maximum responsiveness
            self.ser.write_timeout = 0.001  # 1ms write timeout
            self.ser.inter_byte_timeout = None
            
            # Disable flow control for maximum speed
            self.ser.rtscts = False
            self.ser.dsrdtr = False
            self.ser.xonxoff = False
            
            # Set data format (standard 8N1)
            self.ser.bytesize = serial.EIGHTBITS
            self.ser.parity = serial.PARITY_NONE
            self.ser.stopbits = serial.STOPBITS_ONE
            
            # Open port
            self.ser.open()
            
            # Configure buffer sizes to maximum
            if hasattr(self.ser, 'set_buffer_size'):
                self.ser.set_buffer_size(rx_size=65536, tx_size=65536)  # 64KB buffers
                print(f"✓ Set serial buffer sizes to 64KB")
            
            # Reset buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            print(f"✓ Serial port {self.com_port} configured for {self.baudrate} baud")
            return True
            
        except Exception as e:
            print(f"✗ Error configuring serial port: {e}")
            return False
    
    def connect(self) -> bool:
        """Connect with maximum performance optimization"""
        print(f"\n🚀 Connecting to ultra-high-speed interface...")
        print(f"📡 Port: {self.com_port}")
        print(f"⚡ Baud: {self.baudrate:,} bps")
        
        # Set maximum process priority first
        self._set_maximum_priority()
        
        # Configure and open serial port
        if not self._optimize_serial_port():
            return False
        
        print(f"✅ Connected successfully to {self.com_port}")
        return True
    
    def start_monitoring(self) -> bool:
        """Start ultra-high-speed monitoring with process isolation"""
        if not self.ser or not self.ser.is_open:
            print("✗ Serial port not connected")
            return False
        
        print(f"\n🔥 Starting ULTRA-HIGH-SPEED monitoring...")
        print(f"💾 Buffer size: {self._message_buffer.maxlen:,} messages")
        print(f"📦 Bulk read: {self.bulk_read_size:,} bytes")
        print(f"⚙️  Batch size: {self.process_batch_size:,} messages")
        
        # Clear all buffers
        self._clear_all_buffers()
        
        # Initialize statistics
        self._stats['start_time'] = time.time()
        self._last_stats_time = time.time()
        self._running = True
        
        # Start ultra-high performance threads
        self._start_threads()
        
        print(f"🚀 Monitoring started - using maximum available resources")
        return True
    
    def _clear_all_buffers(self):
        """Clear all buffers for clean start"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            
            with self._lock:
                self._message_buffer.clear()
                self._raw_buffer.clear()
                
        except Exception as e:
            print(f"⚠ Error clearing buffers: {e}")
    
    def _start_threads(self):
        """Start all performance-optimized threads"""
        # Ultra-high speed communication thread
        self._communication_thread = threading.Thread(
            target=self._ultra_high_speed_communication, 
            name="UHSComm"
        )
        self._communication_thread.daemon = False
        self._communication_thread.start()
        
        # Message processing thread
        self._processing_thread = threading.Thread(
            target=self._batch_message_processor, 
            name="UHSProcessor"
        )
        self._processing_thread.daemon = False
        self._processing_thread.start()
        
        # Statistics thread
        self._stats_thread = threading.Thread(
            target=self._statistics_reporter, 
            name="UHSStats"
        )
        self._stats_thread.daemon = False
        self._stats_thread.start()
    
    def _ultra_high_speed_communication(self):
        """Ultra-optimized communication loop for maximum throughput"""
        print(f"🔥 Ultra-high-speed communication thread started (TID: {threading.get_ident()})")
        
        # Local variables for maximum performance
        buffer = self._raw_buffer
        read_size = self.bulk_read_size
        
        try:
            while self._running:
                # Read maximum available data
                bytes_available = self.ser.in_waiting
                if bytes_available > 0:
                    # Read in large chunks for maximum efficiency
                    chunk_size = min(read_size, bytes_available)
                    data = self.ser.read(chunk_size)
                    
                    if data:
                        with self._lock:
                            buffer.extend(data)
                            self._bytes_count_last_second += len(data)
                
                # Micro-sleep for CPU efficiency at ultra-high speeds
                time.sleep(0.00001)  # 0.01ms - minimal but prevents 100% CPU lock
                
        except Exception as e:
            if self._running:
                print(f"✗ Error in communication thread: {e}")
                self._stats['errors'] += 1
    
    def _batch_message_processor(self):
        """Process messages in large batches for maximum efficiency"""
        print(f"⚙️  Batch message processor started (TID: {threading.get_ident()})")
        
        message_batch = []
        
        try:
            while self._running:
                # Extract messages from raw buffer
                extracted_count = self._extract_messages_batch(message_batch)
                
                if extracted_count > 0:
                    # Process entire batch at once
                    self._process_message_batch(message_batch)
                    self._message_count_last_second += extracted_count
                    message_batch.clear()
                
                # Small sleep to prevent overwhelming
                time.sleep(0.0001)  # 0.1ms
                
        except Exception as e:
            if self._running:
                print(f"✗ Error in processing thread: {e}")
                self._stats['errors'] += 1
    
    def _extract_messages_batch(self, message_batch: List) -> int:
        """Extract multiple messages from buffer in one operation"""
        extracted = 0
        
        with self._lock:
            buffer = self._raw_buffer
            
            while len(buffer) >= 5 and extracted < self.process_batch_size:
                # Find message start (0xAA)
                start_idx = buffer.find(0xAA)
                if start_idx == -1:
                    buffer.clear()
                    break
                
                if start_idx > 0:
                    del buffer[:start_idx]
                    continue
                
                if len(buffer) < 2:
                    break
                
                # Get message length
                length_info = buffer[1]
                data_length = length_info & 0x0F
                expected_length = 4 + data_length + 1
                
                if len(buffer) < expected_length:
                    break
                
                # Extract complete message
                message_data = list(buffer[:expected_length])
                
                # Validate end marker
                if message_data[-1] == 0x55:
                    message_batch.append(message_data)
                    extracted += 1
                
                del buffer[:expected_length]
        
        return extracted
    
    def _process_message_batch(self, message_batch: List):
        """Process batch of messages efficiently with proper timestamping"""
        current_time = time.time()
        
        for message_data in message_batch:
            try:
                if len(message_data) < 5:
                    continue
                
                # Extract message components
                header = message_data[0]
                length_info = message_data[1]
                frame_id = (message_data[3] << 8) | message_data[2]
                data_length = length_info & 0x0F
                data = message_data[4:4 + data_length]
                end_code = message_data[-1]
                
                if end_code == 0x55 and len(data) == data_length:
                    # Create enhanced message tuple with all necessary information
                    cob_id = frame_id & 0x7FF
                    message_type = self._determine_message_type(cob_id)
                    
                    # Enhanced message format: (timestamp, cob_id, data, msg_type, msg_index)
                    message = (
                        current_time,           # High precision timestamp
                        cob_id,                # CAN Object ID
                        list(data),            # Data bytes as list
                        message_type,          # Message type string
                        self._total_received   # Unique message index
                    )
                    
                    # Add to buffer
                    with self._buffer_lock:
                        self._message_buffer.append(message)
                        self._total_received += 1
                    
                    self._debug_print(f"Processed message: COB-ID=0x{cob_id:03X}, Type={message_type}, Data={data}", verbose=True)
                    
            except Exception as e:
                self._stats['errors'] += 1
                self._debug_print(f"Error processing message: {e}")
                continue
    
    def _statistics_reporter(self):
        """Report statistics every second without saturating terminal"""
        self._debug_print(f"📊 Statistics reporter started (TID: {threading.get_ident()})")
        
        try:
            while self._running:
                time.sleep(1.0)  # Report every second
                
                current_time = time.time()
                
                with self._lock:
                    # Calculate rates
                    self._stats['messages_per_second'] = self._message_count_last_second
                    self._stats['bytes_per_second'] = self._bytes_count_last_second
                    self._stats['total_messages'] += self._message_count_last_second
                    self._stats['buffer_utilization'] = (len(self._message_buffer) / self._message_buffer.maxlen) * 100
                    self._stats['last_update'] = current_time
                    
                    # Track maximum buffer usage
                    current_buffer_size = len(self._message_buffer)
                    if current_buffer_size > self._stats['max_buffer_size']:
                        self._stats['max_buffer_size'] = current_buffer_size
                    
                    # Create status line
                    uptime = current_time - self._stats['start_time'] if self._stats['start_time'] else 0
                    
                    status = (
                        f"📈 MSG/s: {self._stats['messages_per_second']:6,} | "
                        f"📦 KB/s: {self._stats['bytes_per_second']/1024:6.1f} | "
                        f"🎯 Total: {self._stats['total_messages']:8,} | "
                        f"💾 Buf: {self._stats['buffer_utilization']:5.1f}% | "
                        f"⏱️  Up: {uptime:6.1f}s | "
                        f"❌ Err: {self._stats['errors']:3,}"
                    )
                    
                    # Reset counters
                    self._message_count_last_second = 0
                    self._bytes_count_last_second = 0
                
                # Print status (single line, overwrites previous) - ONLY if debug enabled or if it's the main interface
                if self._debug_enabled or not hasattr(self, '_suppress_stats'):
                    print(f"\r{status}", end="", flush=True)
                
        except Exception as e:
            if self._running:
                self._debug_print(f"Error in statistics thread: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        # Prevent duplicate calls
        if self._stopping or not self._running:
            return
        
        self._stopping = True
        print(f"\n\n🛑 Stopping ultra-high-speed monitoring...")
        
        self._running = False
        
        # Wait for threads to finish
        threads = [
            ('Communication', self._communication_thread),
            ('Processing', self._processing_thread),
            ('Statistics', self._stats_thread)
        ]
        
        for name, thread in threads:
            if thread and thread.is_alive():
                print(f"⏳ Waiting for {name} thread to finish...")
                thread.join(timeout=2.0)
                if thread.is_alive():
                    print(f"⚠ {name} thread did not finish gracefully")
        
        print(f"✅ All threads stopped")
    
    def disconnect(self):
        """Disconnect and cleanup all resources"""
        # Prevent duplicate calls
        if self._disconnected:
            return
        
        self._disconnected = True
        
        # Only stop monitoring if not already stopped
        if not self._stopping:
            self.stop_monitoring()
        
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"📡 Disconnected from {self.com_port}")
        
        # Print final statistics only once
        if not hasattr(self, '_stats_printed'):
            self._stats_printed = True
            self._print_final_stats()
    
    def _print_final_stats(self):
        """Print comprehensive final statistics"""
        if not self._stats['start_time']:
            return
            
        print(f"\n" + "="*80)
        print(f"📊 FINAL PERFORMANCE STATISTICS")
        print(f"="*80)
        
        uptime = time.time() - self._stats['start_time']
        avg_msg_rate = self._stats['total_messages'] / uptime if uptime > 0 else 0
        
        print(f"⏱️  Total uptime:          {uptime:.2f} seconds")
        print(f"📨 Total messages:        {self._stats['total_messages']:,}")
        print(f"📈 Average MSG/s:         {avg_msg_rate:,.1f}")
        print(f"📈 Peak MSG/s:            {max(0, self._stats['messages_per_second']):,}")
        print(f"💾 Max buffer usage:      {self._stats['max_buffer_size']:,} messages")
        print(f"💾 Buffer utilization:    {self._stats['buffer_utilization']:.1f}%")
        print(f"❌ Total errors:          {self._stats['errors']:,}")
        print(f"🔧 Process priority:      {'✓ REALTIME' if self._high_priority_set else '✗ Normal'}")
        print(f"📡 Port configuration:    {self.com_port} @ {self.baudrate:,} baud")
        print(f"="*80)
    
    def get_latest_messages(self, count: int = 100) -> List[Tuple]:
        """Get latest messages (non-blocking)"""
        with self._lock:
            if count >= len(self._message_buffer):
                return list(self._message_buffer)
            else:
                return list(self._message_buffer)[-count:]
    
    def get_statistics(self) -> Dict:
        """Get current statistics"""
        with self._lock:
            return self._stats.copy()
    
    def get_unprocessed_count(self) -> int:
        """Get number of unprocessed messages available for processing"""
        with self._buffer_lock:
            # Simple logic: all messages in buffer are available for processing
            # Once processed, they get cleared from the buffer
            available_count = len(self._message_buffer)
            self._debug_print(f"Unprocessed count: {available_count} (total_received: {self._total_received}, total_cleared: {self._total_cleared})", verbose=True)
            return available_count
    
    def get_messages_batch(self, batch_size: int = 50, start_index: int = 0) -> List[Tuple]:
        """Get a batch of messages for processing without removing them"""
        with self._buffer_lock:
            total_messages = len(self._message_buffer)
            
            if total_messages == 0:
                self._debug_print("No messages in buffer", verbose=True)
                return []
            
            if start_index >= total_messages:
                self._debug_print(f"Batch request beyond buffer: start={start_index}, total={total_messages}")
                return []
            
            end_index = min(start_index + batch_size, total_messages)
            
            # Get messages from buffer starting from the oldest (index 0)
            batch = []
            for i in range(start_index, end_index):
                msg = self._message_buffer[i]
                
                # msg is already in the correct format: (timestamp, cob_id, data, msg_type, msg_index)
                if isinstance(msg, tuple) and len(msg) >= 5:
                    batch.append(msg)
                elif isinstance(msg, tuple) and len(msg) >= 3:
                    # Handle legacy format and convert
                    timestamp, frame_id, data = msg[0], msg[1], msg[2]
                    cob_id = frame_id & 0x7FF
                    message_type = self._determine_message_type(cob_id)
                    
                    batch.append((
                        timestamp,
                        cob_id,
                        data,
                        message_type,
                        i  # Use buffer index
                    ))
            
            self._debug_print(f"Retrieved batch: {len(batch)} messages (start={start_index}, end={end_index})")
            return batch
    
    def clear_processed_messages(self, count: int) -> int:
        """Clear specified number of processed messages from buffer (oldest first)"""
        with self._buffer_lock:
            if count <= 0:
                return 0
            
            # Calculate how many we can actually clear
            clearable = min(count, len(self._message_buffer))
            
            # Remove messages from the left (oldest first)
            for _ in range(clearable):
                if self._message_buffer:
                    self._message_buffer.popleft()
            
            # Update cleared counter
            self._total_cleared += clearable
            
            self._debug_print(f"Cleared {clearable} messages from buffer (requested: {count}, total_cleared: {self._total_cleared})")
            return clearable
    
    def get_buffer_info(self) -> Dict:
        """Get comprehensive information about the current buffer state"""
        with self._buffer_lock:
            buffer_size = len(self._message_buffer)
            oldest_timestamp = None
            newest_timestamp = None
            
            if buffer_size > 0:
                # Messages are stored as tuples: (timestamp, cob_id, data, msg_type, msg_index)
                oldest_msg = self._message_buffer[0]
                newest_msg = self._message_buffer[-1]
                
                # Extract timestamp from tuple (first element)
                if isinstance(oldest_msg, tuple) and len(oldest_msg) > 0:
                    oldest_timestamp = oldest_msg[0]
                if isinstance(newest_msg, tuple) and len(newest_msg) > 0:
                    newest_timestamp = newest_msg[0]
            
            # Available messages = all messages in buffer (since unprocessed messages are what's in buffer)
            available_messages = buffer_size
            
            info = {
                'total_messages': buffer_size,
                'available_messages': available_messages,
                'buffer_capacity': self._message_buffer.maxlen,
                'utilization_percent': (buffer_size / self._message_buffer.maxlen) * 100,
                'oldest_timestamp': oldest_timestamp,
                'newest_timestamp': newest_timestamp,
                'total_received': self._total_received,
                'total_cleared': self._total_cleared
            }
            
            self._debug_print(f"Buffer info: {info}", verbose=True)
            return info
    
    def _determine_message_type(self, cob_id: int) -> str:
        """Determine message type from COB-ID"""
        if 0x180 <= cob_id < 0x200:
            return "TPDO1"
        elif 0x280 <= cob_id < 0x300:
            return "TPDO2"
        elif 0x380 <= cob_id < 0x400:
            return "TPDO3"
        elif 0x480 <= cob_id < 0x500:
            return "TPDO4"
        elif 0x200 <= cob_id < 0x280:
            return "RPDO1"
        elif 0x300 <= cob_id < 0x380:
            return "RPDO2"
        elif 0x400 <= cob_id < 0x480:
            return "RPDO3"
        elif 0x500 <= cob_id < 0x580:
            return "RPDO4"
        elif 0x600 <= cob_id < 0x700:
            return "SDO Rx"
        elif 0x580 <= cob_id < 0x600:
            return "SDO Tx"
        elif cob_id == 0x000:
            return "NMT"
        elif 0x080 <= cob_id < 0x100:
            return "Emergency"
        elif 0x700 <= cob_id < 0x780:
            return "Heartbeat"
        else:
            return "Unknown"
    
    def peek_buffer_range(self, start: int = 0, count: int = 10) -> List[Dict]:
        """Peek at messages in buffer without removing them (for debugging)"""
        with self._buffer_lock:
            total = len(self._message_buffer)
            if start >= total:
                return []
            
            end = min(start + count, total)
            messages = []
            
            for i in range(start, end):
                msg = self._message_buffer[i]
                
                # msg is a tuple: (timestamp, frame_id, data)
                if isinstance(msg, tuple) and len(msg) >= 3:
                    timestamp, frame_id, data = msg[0], msg[1], msg[2]
                    cob_id = frame_id & 0x7FF
                    message_type = self._determine_message_type(cob_id)
                    
                    messages.append({
                        'index': i,
                        'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                        'cob_id': f"0x{cob_id:03X}",
                        'data': data,
                        'type': message_type
                    })
            
            return messages
    
    def process_messages_independently(self):
        """Independent message processing loop"""
        print(f"🔄 Independent message processor started (TID: {threading.get_ident()})")
        
        try:
            while self._running:
                # Get a batch of unprocessed messages
                batch = self.get_messages_batch(self.process_batch_size)
                
                if batch:
                    # TODO: Implement actual message processing logic here
                    # For now, we just print the batch info
                    print(f"📦 Processing batch: {len(batch)} messages")
                    
                    # Simulate processing time
                    time.sleep(0.01)
                    
                    # Clear processed messages from buffer
                    self.clear_processed_messages(len(batch))
                
                else:
                    # No new messages, sleep briefly
                    time.sleep(0.001)
        
        except Exception as e:
            print(f"⚠ Error in independent processor: {e}")
            self._stats['errors'] += 1

    def suppress_stats_output(self, suppress: bool = True):
        """Suppress automatic statistics output (for when used with external processor)"""
        if suppress:
            self._suppress_stats = True
            self._debug_print("Statistics output suppressed")
        else:
            if hasattr(self, '_suppress_stats'):
                delattr(self, '_suppress_stats')
            self._debug_print("Statistics output enabled")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print(f"\n\n🛑 Received signal {signum} - shutting down gracefully...")
    if 'interface' in globals():
        interface.disconnect()
    sys.exit(0)


def main():
    """Main test function"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configuration
    COM_PORT = "COM7"  # Change to your COM port
    BAUDRATE = 2000000  # 2M baud
    
    print(f"🚀 ULTRA-HIGH-SPEED USB-SERIAL CAN INTERFACE TEST")
    print(f"="*60)
    print(f"📡 Target: {COM_PORT} @ {BAUDRATE:,} baud")
    print(f"🎯 Optimized for maximum performance and resource utilization")
    print(f"⚡ Process isolation with REALTIME priority")
    print(f"="*60)
    
    # Create interface
    global interface
    interface = UltraHighSpeedCANInterface(com_port=COM_PORT, baudrate=BAUDRATE)
    
    try:
        # Connect
        if not interface.connect():
            print(f"✗ Failed to connect to {COM_PORT}")
            return
        
        # Start monitoring
        if not interface.start_monitoring():
            print(f"✗ Failed to start monitoring")
            return
        
        print(f"\n🔥 MONITORING ACTIVE - Press Ctrl+C to stop")
        print(f"📊 Statistics will be displayed every second")
        print(f"-" * 80)
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(10)  # Main thread sleeps
        except KeyboardInterrupt:
            print(f"\n\n⌨️  Keyboard interrupt received")
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    
    finally:
        # Cleanup
        interface.disconnect()
        print(f"\n👋 Test completed")


if __name__ == "__main__":
    main()
