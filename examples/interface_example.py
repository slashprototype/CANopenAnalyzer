#!/usr/bin/env python3
"""
Example script showing how to use the new CAN interfaces
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.app_config import AppConfig
from utils.logger import Logger
from interfaces import InterfaceManager, CANMessage

def message_callback(message: CANMessage):
    """Callback function for processing received messages"""
    print(f"Received: COB-ID: 0x{message.cob_id:03X}, "
          f"Node: {message.node_id}, "
          f"Type: {message.message_type}, "
          f"Data: {[hex(b) for b in message.data]}")

def main():
    """Main example function"""
    
    # Initialize configuration and logger
    config = AppConfig()
    logger = Logger()
    
    print("CAN Interface Example")
    print("====================")
    
    # Show available interfaces
    interface_manager = InterfaceManager(config, logger)
    available = interface_manager.get_available_interfaces()
    print(f"Available interfaces: {available}")
    
    # Initialize interface
    if not interface_manager.initialize_interface():
        print("Failed to initialize interface")
        return
    
    print(f"Initialized interface: {config.can_config.interface}")
    
    # Configure interface based on type
    if config.can_config.interface == "usb_serial":
        print(f"COM Port: {config.can_config.com_port}")
        print(f"Baudrate: {config.can_config.serial_baudrate}")
        
        # You might want to prompt user for COM port
        # com_port = input(f"Enter COM port [{config.can_config.com_port}]: ").strip()
        # if com_port:
        #     config.can_config.com_port = com_port
    
    # Connect to interface
    print("Connecting to interface...")
    if not interface_manager.connect():
        print("Failed to connect to interface")
        return
    
    print("Connected successfully!")
    
    # Add message callback
    interface_manager.add_message_callback(message_callback)
    
    # Start monitoring
    print("Starting message monitoring...")
    if not interface_manager.start_monitoring():
        print("Failed to start monitoring")
        interface_manager.disconnect()
        return
    
    print("Monitoring started. Press Ctrl+C to stop.")
    
    try:
        # Example: Send some SDO messages (if using USB Serial)
        if config.can_config.interface == "usb_serial":
            print("\\nSending example SDO read requests...")
            
            # Read heartbeat producer time (index 0x1017, subindex 0x00)
            sdo_request = {
                'index': 0x1017,
                'subindex': 0x00,
                'size': 32,  # 4 bytes
                'value': 0,
                'is_read': True
            }
            
            interface_manager.send_data(sdo_request)
            time.sleep(1)
            
            # Read device type (index 0x1000, subindex 0x00)
            sdo_request = {
                'index': 0x1000,
                'subindex': 0x00,
                'size': 32,  # 4 bytes
                'value': 0,
                'is_read': True
            }
            
            interface_manager.send_data(sdo_request)
        
        # Monitor for messages
        start_time = time.time()
        while True:
            time.sleep(1)
            
            # Show statistics every 10 seconds
            if int(time.time() - start_time) % 10 == 0:
                messages = interface_manager.get_messages_dictionary()
                print(f"\\nActive message IDs: {len(messages)}")
                for msg_id, data in messages.items():
                    print(f"  {msg_id}: {[hex(b) for b in data]}")
                print()
            
    except KeyboardInterrupt:
        print("\\nStopping...")
    
    finally:
        # Clean up
        print("Stopping monitoring...")
        interface_manager.stop_monitoring()
        
        print("Disconnecting...")
        interface_manager.disconnect()
        
        print("Done.")

if __name__ == "__main__":
    main()
