#!/usr/bin/env python3
"""
Test script for Monitor Module with USB Serial Interface
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import flet as ft
from config.app_config import AppConfig
from utils.logger import Logger
from modules.monitor_module import MonitorModule

def main(page: ft.Page):
    """Main test application"""
    page.title = "CANopen Monitor Test"
    page.window_width = 1200
    page.window_height = 800
    
    # Initialize configuration
    config = AppConfig()
    
    # Configure for USB Serial interface
    config.can_config.interface = "usb_serial"
    config.can_config.com_port = "COM3"  # Change this to your COM port
    config.can_config.serial_baudrate = 115200
    
    print(f"Using interface: {config.can_config.interface}")
    print(f"COM Port: {config.can_config.com_port}")
    print(f"Baudrate: {config.can_config.serial_baudrate}")
    
    # Initialize logger
    logger = Logger()
    
    # Create monitor module
    monitor = MonitorModule(page, config, logger)
    monitor.initialize()
    
    # Create simple interface
    title = ft.Text(
        "CANopen Monitor Test - USB Serial Interface",
        size=20,
        weight=ft.FontWeight.BOLD
    )
    
    instructions = ft.Text(
        "Instructions:\\n"
        "1. Make sure your USB-Serial CAN converter is connected\\n"
        "2. Update the COM port in this script if needed\\n"
        "3. Click 'Connect' to connect to the interface\\n"
        "4. Click 'Start Monitor' to begin capturing messages\\n"
        "5. Messages will appear in the table below",
        size=12
    )
    
    # Add everything to page
    page.add(
        ft.Container(
            content=ft.Column([
                title,
                ft.Divider(),
                instructions,
                ft.Divider(),
                monitor
            ]),
            padding=20
        )
    )

def run_test():
    """Run the test application"""
    print("Starting CANopen Monitor Test...")
    print("This will test the USB Serial interface integration.")
    print("Make sure your USB-Serial CAN converter is connected!")
    print()
    
    ft.app(target=main)

if __name__ == "__main__":
    run_test()
