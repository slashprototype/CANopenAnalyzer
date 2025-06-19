#!/usr/bin/env python3
"""
Simple test script for USB Serial Interface
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.app_config import AppConfig
from utils.logger import Logger
from interfaces import InterfaceManager

def message_callback(message):
    """Callback function for processing received messages"""
    print(f"[{message.timestamp.strftime('%H:%M:%S.%f')[:-3]}] "
          f"COB-ID: 0x{message.cob_id:03X} | "
          f"Node: {message.node_id:2d} | "
          f"Type: {message.message_type:10s} | "
          f"Data: {' '.join([f'{b:02X}' for b in message.data])}")

def main():
    """Main test function"""
    print("USB Serial CAN Interface Test")
    print("=" * 50)
    
    # Create configuration
    config = AppConfig()
    config.can_config.interface = "usb_serial"
    
    # Prompt for COM port
    com_port = input(f"Enter COM port [{config.can_config.com_port}]: ").strip()
    if com_port:
        config.can_config.com_port = com_port
    
    baudrate = input(f"Enter baudrate [{config.can_config.serial_baudrate}]: ").strip()
    if baudrate:
        config.can_config.serial_baudrate = int(baudrate)
    
    print(f"\\nUsing: {config.can_config.com_port} @ {config.can_config.serial_baudrate} baud")
    
    # Create logger and interface manager
    logger = Logger()
    interface_manager = InterfaceManager(config, logger)
    
    # Initialize interface
    print("\\nInitializing interface...")
    if not interface_manager.initialize_interface():
        print("❌ Failed to initialize interface")
        return
    
    print("✅ Interface initialized")
    
    # Connect
    print("\\nConnecting to interface...")
    if not interface_manager.connect():
        print("❌ Failed to connect to interface")
        return
    
    print("✅ Connected successfully")
    
    # Add message callback
    interface_manager.add_message_callback(message_callback)
    
    # Start monitoring
    print("\\nStarting message monitoring...")
    if not interface_manager.start_monitoring():
        print("❌ Failed to start monitoring")
        interface_manager.disconnect()
        return
    
    print("✅ Monitoring started")
    print("\\nMonitoring CAN messages... Press Ctrl+C to stop\\n")
    
    try:
        # Monitor for a while and show some stats
        start_time = time.time()
        last_stats_time = start_time
        
        while True:
            time.sleep(1)
            
            # Show stats every 5 seconds
            current_time = time.time()
            if current_time - last_stats_time >= 5:
                messages = interface_manager.get_messages_dictionary()
                print(f"\\n--- Stats (Runtime: {current_time - start_time:.1f}s) ---")
                print(f"Active message IDs: {len(messages)}")
                for msg_id, data in list(messages.items())[:5]:  # Show first 5
                    print(f"  {msg_id}: {' '.join([f'{b:02X}' for b in data])}")
                if len(messages) > 5:
                    print(f"  ... and {len(messages) - 5} more")
                print()
                last_stats_time = current_time
            
            # Test sending some data every 10 seconds
            if int(current_time - start_time) % 10 == 0 and int(current_time - start_time) > 0:
                print("\\n--- Sending test SDO read request ---")
                test_data = {
                    'index': 0x1000,      # Device type
                    'subindex': 0x00,
                    'size': 32,           # 4 bytes
                    'value': 0,
                    'is_read': True
                }
                
                if interface_manager.send_data(test_data):
                    print("✅ Test SDO request sent")
                else:
                    print("❌ Failed to send test request")
                print()
    
    except KeyboardInterrupt:
        print("\\n\\nStopping...")
    
    finally:
        # Clean up
        print("Stopping monitoring...")
        interface_manager.stop_monitoring()
        
        print("Disconnecting...")
        interface_manager.disconnect()
        
        print("✅ Test completed")

if __name__ == "__main__":
    main()
