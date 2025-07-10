#!/usr/bin/env python3
"""
Independent Message Processor Module

PURPOSE:
This module provides an independent message processing system that works with the
UltraHighSpeedCANInterface to process CAN messages in batches. It operates in its own
thread, continuously retrieving message batches from the interface, processing them
according to CANopen protocol rules, and maintaining processing statistics.

KEY FEATURES:
- Independent batch processing of CAN messages
- Configurable batch sizes and processing intervals
- Real-time processing statistics and monitoring
- Automatic buffer cleanup and management
- CANopen protocol-aware message processing
- Debug controls for development and troubleshooting
- Graceful shutdown and error handling

Processes CAN messages from USB Serial Interface in batches
Clears processed messages from the interface buffer
"""

import threading
import time
import signal
import sys
from typing import List, Tuple, Dict, Optional
from datetime import datetime

# Import new modules
from can_message import CANMessage, CANMessageType
from can_message_stack import CANMessageStack

class CANMessageProcessor:
    """
    Independent processor for CAN messages from USB Serial Interface
    Processes messages in batches and manages buffer cleanup
    Now includes organized message stack by COB-ID
    """
    
    def __init__(self, serial_interface, batch_size: int = 50, processing_interval: float = 0.5, debug: bool = False):
        """
        Initialize message processor with integrated message stack
        
        Args:
            serial_interface: Instance of UltraHighSpeedCANInterface
            batch_size: Number of messages to process in each batch
            processing_interval: Interval between processing cycles (seconds)
            debug: Enable debug output
        """
        self.serial_interface = serial_interface
        self.batch_size = batch_size
        self.processing_interval = processing_interval
        
        # Debug control
        self._debug_enabled = debug
        self._verbose_debug = False
        
        # Initialize message stack
        self.message_stack = CANMessageStack(max_age_seconds=300.0, debug=debug)
        
        # Processing control
        self._processing_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        
        # Processing statistics
        self._stats = {
            'total_processed': 0,
            'total_batches': 0,
            'messages_per_second': 0,
            'average_batch_size': 0,
            'processing_time_avg': 0.0,
            'buffer_cleanups': 0,
            'start_time': None,
            'last_processing_time': 0.0
        }
        
        # Message processing tracking
        self._processed_count_last_second = 0
        self._last_stats_time = time.time()
        self._processing_times = []
        
        # Configuration
        self.max_processing_time_samples = 100  # For rolling average
        self.stats_display_interval = 1.0  # Display stats every second
    
    def enable_debug(self, enabled: bool = True, verbose: bool = False):
        """Enable or disable debug output"""
        self._debug_enabled = enabled
        self._verbose_debug = verbose
        if enabled:
            self._debug_print(f"🐛 Debug enabled (verbose: {verbose})")
    
    def _debug_print(self, message: str, verbose: bool = False):
        """Print debug message if debugging is enabled"""
        if self._debug_enabled and (not verbose or self._verbose_debug):
            print(f"[DEBUG-PROCESSOR] {message}")
    
    def start_processing(self) -> bool:
        """Start independent message processing"""
        if self._running:
            print("⚠ Message processor is already running")
            return False
        
        if not self.serial_interface:
            print("✗ No serial interface provided")
            return False
        
        # Check required methods
        required_methods = ['get_messages_batch', 'clear_processed_messages', 'get_unprocessed_count']
        for method in required_methods:
            if not hasattr(self.serial_interface, method):
                print(f"✗ Serial interface missing required method: {method}")
                return False
        
        # Suppress interface stats output to avoid confusion
        if hasattr(self.serial_interface, 'suppress_stats_output'):
            self.serial_interface.suppress_stats_output(True)
        
        print(f"\n🔄 Starting Independent Message Processor")
        print(f"📦 Batch size: {self.batch_size} messages")
        print(f"⏱️  Processing interval: {self.processing_interval:.3f}s")
        print(f"🐛 Debug mode: {'ON' if self._debug_enabled else 'OFF'}")
        print(f"="*60)
        
        # Initialize statistics
        self._stats['start_time'] = time.time()
        self._last_stats_time = time.time()
        self._running = True
        
        # Start processing thread
        self._processing_thread = threading.Thread(
            target=self._processing_loop, 
            name="CANMsgProcessor"
        )
        self._processing_thread.daemon = False
        self._processing_thread.start()
        
        print(f"🚀 Message processor started (TID: {threading.get_ident()})")
        self._debug_print("Processing thread started successfully")
        return True
    
    def stop_processing(self):
        """Stop message processing"""
        print(f"\n🛑 Stopping message processor...")
        
        self._running = False
        
        if self._processing_thread and self._processing_thread.is_alive():
            print(f"⏳ Waiting for processing thread to finish...")
            self._processing_thread.join(timeout=3.0)
            if self._processing_thread.is_alive():
                print(f"⚠ Processing thread did not finish gracefully")
            else:
                print(f"✅ Processing thread stopped")
        
        self._print_final_stats()
    
    def _processing_loop(self):
        """Main processing loop - runs independently"""
        print(f"🔄 Processing loop started (TID: {threading.get_ident()})")
        
        last_stats_display = time.time()
        
        try:
            while self._running:
                cycle_start = time.time()
                
                # Get buffer information
                buffer_info = self._get_buffer_info()
                
                if buffer_info['available_messages'] > 0:
                    # Process available messages in batches
                    processed_count = self._process_available_messages(buffer_info)
                    
                    if processed_count > 0:
                        self._processed_count_last_second += processed_count
                
                # Display statistics every second
                current_time = time.time()
                if current_time - last_stats_display >= self.stats_display_interval:
                    self._update_and_display_stats()
                    last_stats_display = current_time
                
                # Sleep for the remaining interval time
                cycle_time = time.time() - cycle_start
                remaining_time = max(0, self.processing_interval - cycle_time)
                if remaining_time > 0:
                    time.sleep(remaining_time)
                
        except Exception as e:
            if self._running:
                print(f"\n✗ Error in processing loop: {e}")
    
    def _get_buffer_info(self) -> Dict:
        """Get current buffer information from serial interface"""
        try:
            if hasattr(self.serial_interface, 'get_buffer_info'):
                info = self.serial_interface.get_buffer_info()
                self._debug_print(f"Buffer info retrieved: {info}", verbose=True)
            else:
                # Fallback for interfaces without get_buffer_info
                available_messages = self.serial_interface.get_unprocessed_count() if hasattr(self.serial_interface, 'get_unprocessed_count') else 0
                info = {
                    'available_messages': available_messages,
                    'utilization_percent': 0.0
                }
                self._debug_print(f"Using fallback buffer info: {info}")
            
            return info
        except Exception as e:
            self._debug_print(f"Error getting buffer info: {e}")
            print(f"⚠ Error getting buffer info: {e}")
            return {'available_messages': 0, 'utilization_percent': 0.0}
    
    def _process_available_messages(self, buffer_info: Dict) -> int:
        """Process all available messages in batches"""
        total_processed = 0
        available_count = buffer_info.get('available_messages', 0)
        
        if available_count == 0:
            self._debug_print("No messages available for processing", verbose=True)
            return 0
        
        self._debug_print(f"Processing {available_count} available messages")
        
        # Process all available messages starting from index 0 (oldest first)
        messages_remaining = available_count
        
        while messages_remaining > 0 and self._running:
            # Calculate batch size for this iteration
            current_batch_size = min(self.batch_size, messages_remaining)
            
            # Always get messages from index 0 since we clear them after processing
            batch_start_time = time.time()
            message_batch = self._get_message_batch(current_batch_size, 0)
            
            if not message_batch:
                self._debug_print(f"No message batch retrieved, breaking")
                break
            
            actual_batch_size = len(message_batch)
            
            # Process the batch
            processed_count = self._process_message_batch(message_batch)
            
            if processed_count > 0:
                # Clear processed messages from interface buffer (from the beginning)
                cleared_count = self._clear_processed_messages(processed_count)
                total_processed += processed_count
                messages_remaining -= processed_count
                
                # Update statistics
                batch_time = time.time() - batch_start_time
                self._update_processing_stats(processed_count, batch_time)
                
                # Print batch information only if debug is enabled
                if self._debug_enabled:
                    self._print_batch_info(processed_count, cleared_count, batch_time, message_batch)
                
                self._debug_print(f"Processed {processed_count} messages, {messages_remaining} remaining")
            else:
                self._debug_print(f"No messages processed in batch, breaking")
                break
            
            # Small delay between batches to prevent overwhelming
            if self._running and messages_remaining > 0:
                time.sleep(0.001)  # 1ms delay between batches
        
        self._debug_print(f"Completed processing: {total_processed} total messages processed")
        return total_processed
    
    def _get_message_batch(self, batch_size: int, start_index: int) -> List[Tuple]:
        """Get batch of messages from serial interface"""
        try:
            batch = self.serial_interface.get_messages_batch(batch_size, start_index)
            self._debug_print(f"Retrieved batch: {len(batch)} messages (requested: {batch_size}, start: {start_index})", verbose=True)
            return batch
        except Exception as e:
            self._debug_print(f"Error getting message batch: {e}")
            print(f"⚠ Error getting message batch: {e}")
            return []
    
    def _clear_processed_messages(self, count: int) -> int:
        """Clear processed messages from interface buffer"""
        try:
            cleared = self.serial_interface.clear_processed_messages(count)
            self._debug_print(f"Cleared {cleared} messages from interface buffer (requested: {count})")
            return cleared
        except Exception as e:
            self._debug_print(f"Error clearing processed messages: {e}")
            print(f"⚠ Error clearing processed messages: {e}")
            return 0

    def _process_message_batch(self, message_batch: List[Tuple]) -> int:
        """
        Process a batch of messages using new modular structure
        
        Returns: Number of successfully processed messages
        """
        processed_count = 0
        
        try:
            self._debug_print(f"Processing batch of {len(message_batch)} messages", verbose=True)
            
            for i, message_tuple in enumerate(message_batch):
                try:
                    # Debug: Print the actual message tuple format
                    if i == 0:  # Only for the first message to avoid spam
                        self._debug_print(f"Message tuple format: {type(message_tuple)}, length: {len(message_tuple) if isinstance(message_tuple, tuple) else 'N/A'}")
                        self._debug_print(f"First message content: {message_tuple}")
                    
                    # Validate message tuple format
                    if not isinstance(message_tuple, tuple) or len(message_tuple) < 3:
                        self._debug_print(f"Invalid message format at index {i}: {message_tuple}")
                        continue
                    
                    # Create CANMessage object
                    can_message = CANMessage.from_tuple(message_tuple)
                    
                    # Validate message
                    if not can_message.is_valid():
                        self._debug_print(f"Invalid CAN message at index {i}: {can_message}")
                        continue
                    
                    # Process message using new architecture
                    success = self._process_can_message(can_message)
                    
                    if success:
                        processed_count += 1
                        self._debug_print(f"Processed message {i}: {can_message}", verbose=True)
                    else:
                        self._debug_print(f"Failed to process message at index {i}: {can_message}")
                        continue
                        
                except Exception as e:
                    self._debug_print(f"Error processing individual message at index {i}: {e}")
                    self._debug_print(f"Message content: {message_tuple}")
                    continue
            
        except Exception as e:
            self._debug_print(f"Error in batch processing: {e}")
            print(f"✗ Error processing message batch: {e}")
        
        self._debug_print(f"Batch processing complete: {processed_count}/{len(message_batch)} messages processed")
        return processed_count
    
    def _process_can_message(self, can_message: CANMessage) -> bool:
        """
        Process individual CAN message using modular approach
        
        Args:
            can_message: CANMessage object to process
            
        Returns:
            True if processing successful
        """
        try:
            # 1. Add/update message in stack (organized by COB-ID)
            stack_success = self.message_stack.update_message(can_message)
            
            if not stack_success:
                self._debug_print(f"Failed to update message stack for COB-ID 0x{can_message.cob_id:03X}")
                return False
            
            # 2. Process message based on type using modular functions
            if CANMessageType.is_pdo(can_message.msg_type):
                result = self._process_pdo_message(can_message)
            elif CANMessageType.is_sdo(can_message.msg_type):
                result = self._process_sdo_message(can_message)
            elif can_message.msg_type == CANMessageType.HEARTBEAT:
                result = self._process_heartbeat_message(can_message)
            elif can_message.msg_type == CANMessageType.EMERGENCY:
                result = self._process_emergency_message(can_message)
            elif can_message.msg_type == CANMessageType.NMT:
                result = self._process_nmt_message(can_message)
            else:
                result = self._process_generic_message(can_message)
            
            if result:
                self._debug_print(f"Successfully processed {can_message.msg_type} message: COB-ID=0x{can_message.cob_id:03X}", verbose=True)
            
            return result
            
        except Exception as e:
            self._debug_print(f"Error processing CAN message: {e}")
            return False
    
    def _process_pdo_message(self, message: CANMessage) -> bool:
        """Process PDO message"""
        try:
            self._debug_print(f"PDO from node {message.node_id}: {len(message.data)} bytes", verbose=True)
            # TODO: Implement specific PDO processing logic
            return len(message.data) >= 1
        except Exception as e:
            self._debug_print(f"Error in PDO processing: {e}")
            return False
    
    def _process_sdo_message(self, message: CANMessage) -> bool:
        """Process SDO message"""
        try:
            if len(message.data) >= 4:
                command = message.data[0]
                self._debug_print(f"SDO command 0x{command:02X} from node {message.node_id}: {len(message.data)} bytes", verbose=True)
                # TODO: Implement specific SDO processing logic
                return True
            return False
        except Exception as e:
            self._debug_print(f"Error in SDO processing: {e}")
            return False
    
    def _process_heartbeat_message(self, message: CANMessage) -> bool:
        """Process Heartbeat message"""
        try:
            if len(message.data) == 1:
                nmt_state = message.data[0]
                valid_states = [0, 4, 5, 127]  # Valid NMT states
                is_valid = nmt_state in valid_states
                self._debug_print(f"Heartbeat from node {message.node_id}, state: {nmt_state} ({'valid' if is_valid else 'invalid'})", verbose=True)
                # TODO: Implement heartbeat monitoring logic
                return is_valid
            return False
        except Exception as e:
            self._debug_print(f"Error in Heartbeat processing: {e}")
            return False
    
    def _process_emergency_message(self, message: CANMessage) -> bool:
        """Process Emergency message"""
        try:
            if len(message.data) >= 2:
                error_code = (message.data[1] << 8) | message.data[0]
                self._debug_print(f"Emergency from node {message.node_id}, error: 0x{error_code:04X}", verbose=True)
                # TODO: Implement emergency handling logic
                return True
            return False
        except Exception as e:
            self._debug_print(f"Error in Emergency processing: {e}")
            return False
    
    def _process_nmt_message(self, message: CANMessage) -> bool:
        """Process NMT message"""
        try:
            if len(message.data) >= 2:
                command = message.data[0]
                node_id = message.data[1]
                self._debug_print(f"NMT command {command} for node {node_id}", verbose=True)
                # TODO: Implement NMT processing logic
                return True
            return False
        except Exception as e:
            self._debug_print(f"Error in NMT processing: {e}")
            return False
    
    def _process_generic_message(self, message: CANMessage) -> bool:
        """Process generic/unknown message"""
        try:
            self._debug_print(f"Generic message COB-ID=0x{message.cob_id:03X}: {len(message.data)} bytes", verbose=True)
            # TODO: Implement generic processing logic
            return True
        except Exception as e:
            self._debug_print(f"Error in generic processing: {e}")
            return False
    
    def get_message_stack_statistics(self) -> Dict:
        """Get statistics from message stack"""
        return self.message_stack.get_statistics()
    
    def get_network_summary(self) -> Dict:
        """Get comprehensive network summary"""
        return self.message_stack.get_network_summary()
    
    def get_active_nodes(self) -> List[int]:
        """Get list of active nodes"""
        return self.message_stack.get_active_nodes()
    
    def get_message_by_cobid(self, cob_id: int) -> Optional[CANMessage]:
        """Get latest message for specific COB-ID"""
        return self.message_stack.get_message(cob_id)
    
    def get_messages_by_node(self, node_id: int) -> List[CANMessage]:
        """Get all latest messages from specific node"""
        return self.message_stack.get_messages_by_node(node_id)

    def _update_processing_stats(self, processed_count: int, processing_time: float):
        """Update processing statistics"""
        with self._lock:
            self._stats['total_processed'] += processed_count
            self._stats['total_batches'] += 1
            
            # Track processing times for average
            self._processing_times.append(processing_time)
            if len(self._processing_times) > self.max_processing_time_samples:
                self._processing_times.pop(0)
            
            # Calculate averages
            if self._processing_times:
                self._stats['processing_time_avg'] = sum(self._processing_times) / len(self._processing_times)
            
            if self._stats['total_batches'] > 0:
                self._stats['average_batch_size'] = self._stats['total_processed'] / self._stats['total_batches']
    
    def _print_batch_info(self, processed: int, cleared: int, batch_time: float, message_batch: List):
        """Print information about processed batch (only when debug is enabled)"""
        if not self._debug_enabled:
            return
            
        if len(message_batch) > 0:
            # Extract message types for summary
            msg_types = {}
            for message_tuple in message_batch:
                if len(message_tuple) >= 4:
                    msg_type = message_tuple[3]  # msg_type is at index 3
                    msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
            
            types_summary = ", ".join([f"{t}:{c}" for t, c in msg_types.items()])
            
            print(f"📦 Batch: {processed:3d} processed, {cleared:3d} cleared | "
                  f"⏱️ {batch_time*1000:5.2f}ms | Types: {types_summary}")
    
    def _simulate_message_processing(self, timestamp: float, cob_id: int, data: List[int], msg_type: str) -> bool:
        """
        Simulate message processing
        Replace this with actual processing logic
        """
        try:
            # SIMULATION: Just validate the message structure
            if not isinstance(data, list) or len(data) > 8:
                self._debug_print(f"Invalid data format: {data}")
                return False
            
            # SIMULATION: Simple processing based on message type
            if msg_type in ["TPDO1", "TPDO2", "TPDO3", "TPDO4"]:
                # Process TPDO messages
                result = self._process_tpdo_simulation(cob_id, data)
            elif msg_type in ["SDO Tx", "SDO Rx"]:
                # Process SDO messages
                result = self._process_sdo_simulation(cob_id, data)
            elif msg_type == "Heartbeat":
                # Process Heartbeat messages
                result = self._process_heartbeat_simulation(cob_id, data)
            else:
                # Process other message types
                result = self._process_generic_simulation(cob_id, data)
            
            if result:
                self._debug_print(f"Successfully processed {msg_type} message: COB-ID=0x{cob_id:03X}, Data={data}", verbose=True)
            
            return result
            
        except Exception as e:
            self._debug_print(f"Error in message processing simulation: {e}")
            return False
    
    def _process_tpdo_simulation(self, cob_id: int, data: List[int]) -> bool:
        """Simulate TPDO processing"""
        try:
            # Extract node ID from COB-ID
            node_id = cob_id & 0x7F
            
            # SIMULATION: Just check data integrity
            if len(data) >= 1:
                self._debug_print(f"TPDO from node {node_id}: {len(data)} bytes", verbose=True)
                return True
            return False
        except Exception as e:
            self._debug_print(f"Error in TPDO simulation: {e}")
            return False
    
    def _process_sdo_simulation(self, cob_id: int, data: List[int]) -> bool:
        """Simulate SDO processing"""
        try:
            if len(data) >= 4:
                command = data[0]
                # SIMULATION: Just validate SDO command structure
                self._debug_print(f"SDO command 0x{command:02X}: {len(data)} bytes", verbose=True)
                return True
            return False
        except Exception as e:
            self._debug_print(f"Error in SDO simulation: {e}")
            return False
    
    def _process_heartbeat_simulation(self, cob_id: int, data: List[int]) -> bool:
        """Simulate Heartbeat processing"""
        try:
            if len(data) == 1:
                nmt_state = data[0]
                node_id = cob_id & 0x7F
                # SIMULATION: Validate NMT state
                valid_states = [0, 4, 5, 127]  # Valid NMT states
                is_valid = nmt_state in valid_states
                self._debug_print(f"Heartbeat from node {node_id}, state: {nmt_state} ({'valid' if is_valid else 'invalid'})", verbose=True)
                return is_valid
            return False
        except Exception as e:
            self._debug_print(f"Error in Heartbeat simulation: {e}")
            return False
    
    def _process_generic_simulation(self, cob_id: int, data: List[int]) -> bool:
        """Simulate generic message processing"""
        try:
            # SIMULATION: Always successful for other message types
            self._debug_print(f"Generic message COB-ID=0x{cob_id:03X}: {len(data)} bytes", verbose=True)
            return True
        except Exception as e:
            self._debug_print(f"Error in generic simulation: {e}")
            return False

    def _update_and_display_stats(self):
        """Update and display processing statistics including stack info"""
        current_time = time.time()
        
        with self._lock:
            # Calculate messages per second
            self._stats['messages_per_second'] = self._processed_count_last_second
            self._stats['last_processing_time'] = current_time
            
            # Get buffer info for display
            buffer_info = {}
            try:
                buffer_info = self.serial_interface.get_buffer_info()
            except:
                pass
            
            # Get stack statistics
            stack_stats = self.message_stack.get_statistics()
            
            # Create status line
            uptime = current_time - self._stats['start_time'] if self._stats['start_time'] else 0
            avg_rate = self._stats['total_processed'] / uptime if uptime > 0 else 0
            
            # Include stack information in processor stats
            buffer_util = buffer_info.get('utilization_percent', 0.0)
            available_msgs = buffer_info.get('available_messages', 0)
            active_cobids = stack_stats.get('active_cobids', 0)
            active_nodes = stack_stats.get('active_nodes', 0)
            
            status = (
                f"🔄 Proc/s: {self._stats['messages_per_second']:4,} | "
                f"📊 Total: {self._stats['total_processed']:6,} | "
                f"📦 Batches: {self._stats['total_batches']:4,} | "
                f"⚡ Avg: {avg_rate:6.1f}/s | "
                f"💾 Buf: {buffer_util:4.1f}% | "
                f"📋 Avail: {available_msgs:4,} | "
                f"🏠 COBs: {active_cobids:3,} | "
                f"👥 Nodes: {active_nodes:2,} | "
                f"⏱️ ProcTime: {self._stats['processing_time_avg']*1000:5.2f}ms | "
                f"🕒 Up: {uptime:6.1f}s"
            )
            
            # Reset counter
            self._processed_count_last_second = 0
        
        # Print status (single line, overwrites previous)
        print(f"\r{status}", end="", flush=True)
    
    def _print_final_stats(self):
        """Print comprehensive final statistics"""
        if not self._stats['start_time']:
            return
            
        print(f"\n" + "="*80)
        print(f"🔄 MESSAGE PROCESSOR FINAL STATISTICS")
        print(f"="*80)
        
        uptime = time.time() - self._stats['start_time']
        avg_rate = self._stats['total_processed'] / uptime if uptime > 0 else 0
        
        print(f"⏱️  Total runtime:         {uptime:.2f} seconds")
        print(f"📨 Total processed:       {self._stats['total_processed']:,} messages")
        print(f"📦 Total batches:         {self._stats['total_batches']:,}")
        print(f"📈 Average rate:          {avg_rate:,.1f} messages/second")
        print(f"📈 Peak rate:             {max(0, self._stats['messages_per_second']):,} messages/second")
        print(f"📦 Average batch size:    {self._stats['average_batch_size']:.1f} messages")
        print(f"⏱️  Average proc time:     {self._stats['processing_time_avg']*1000:.2f}ms per batch")
        print(f"🧹 Buffer cleanups:       {self._stats['buffer_cleanups']:,}")
        print(f"⚙️  Batch size config:     {self.batch_size} messages")
        print(f"⏱️  Processing interval:   {self.processing_interval:.3f} seconds")
        print(f"="*80)
    
    def get_statistics(self) -> Dict:
        """Get current processing statistics"""
        with self._lock:
            stats = self._stats.copy()
            stats['is_running'] = self._running
            return stats


# Global flag to prevent duplicate cleanup
_cleanup_started = False

def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    global _cleanup_started
    
    if _cleanup_started:
        print(f"\n⚠ Cleanup already in progress...")
        return
    
    _cleanup_started = True
    print(f"\n\n🛑 Received signal {signum} - shutting down gracefully...")
    
    try:
        if 'processor' in globals() and processor:
            processor.stop_processing()
        if 'interface' in globals() and interface:
            interface.disconnect()
    except Exception as e:
        print(f"⚠ Error during cleanup: {e}")
    
    sys.exit(0)


def main():
    """Test the message processor with USB Serial Interface and new architecture"""
    global _cleanup_started
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Import the USB Serial Interface
    try:
        from usb_serial_interface import UltraHighSpeedCANInterface
    except ImportError:
        print("✗ Could not import UltraHighSpeedCANInterface")
        print("Make sure usb_serial_interface.py is in the same directory")
        return
    
    # Configuration
    COM_PORT = "COM7"
    BAUDRATE = 2000000
    BATCH_SIZE = 25  # Smaller batch size for better responsiveness
    PROCESSING_INTERVAL = 0.05  # Process every 50ms for better real-time response
    DEBUG_ENABLED = False  # Set to True to see detailed processing
    
    print(f"🔄 CAN MESSAGE PROCESSOR TEST - MODULAR ARCHITECTURE")
    print(f"="*60)
    print(f"📡 Interface: {COM_PORT} @ {BAUDRATE:,} baud")
    print(f"📦 Batch size: {BATCH_SIZE} messages")
    print(f"⏱️  Processing interval: {PROCESSING_INTERVAL}s")
    print(f"🐛 Debug: {'ON' if DEBUG_ENABLED else 'OFF'}")
    print(f"🏗️  Features: Modular CAN messages + COB-ID organized stack")
    print(f"="*60)
    
    # Create interface with debug disabled to reduce noise
    global interface, processor
    interface = UltraHighSpeedCANInterface(com_port=COM_PORT, baudrate=BAUDRATE, debug=False)
    
    try:
        # Connect interface
        if not interface.connect():
            print(f"✗ Failed to connect to {COM_PORT}")
            return
        
        # Start interface monitoring
        if not interface.start_monitoring():
            print(f"✗ Failed to start interface monitoring")
            return
        
        print(f"✅ Interface connected and monitoring")
        
        # Create and start message processor with new architecture
        processor = CANMessageProcessor(
            serial_interface=interface,
            batch_size=BATCH_SIZE,
            processing_interval=PROCESSING_INTERVAL,
            debug=DEBUG_ENABLED
        )
        
        if not processor.start_processing():
            print(f"✗ Failed to start message processor")
            return
        
        print(f"\n🔥 SYSTEM ACTIVE - Modular processing with COB-ID stack")
        print(f"📊 Processing statistics will be displayed every second")
        print(f"💡 Messages are organized by COB-ID (latest per COB-ID)")
        print(f"Press Ctrl+C to stop")
        print(f"-" * 80)
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(10)  # Main thread sleeps
                
                # Optionally display network summary every 10 seconds
                if DEBUG_ENABLED:
                    summary = processor.get_network_summary()
                    print(f"\n📊 Network: {summary['total_active_nodes']} nodes, {summary['total_active_cobids']} COB-IDs")
        except KeyboardInterrupt:
            print(f"\n\n⌨️  Keyboard interrupt received")
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
    
    finally:
        # Only cleanup if not already done by signal handler
        if not _cleanup_started:
            _cleanup_started = True
            if 'processor' in locals():
                processor.stop_processing()
            interface.disconnect()
        print(f"\n👋 Test completed")


if __name__ == "__main__":
    main()
