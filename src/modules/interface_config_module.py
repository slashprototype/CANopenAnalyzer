import flet as ft
from typing import Any
import serial.tools.list_ports
import json
import os
from interfaces import InterfaceManager

class InterfaceConfigModule(ft.Column):
    """Module for configuring CAN interfaces"""
    
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: InterfaceManager = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        # Use singleton instance
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        
        # Callback for notifying other modules about connection changes
        self.connection_change_callback = None
        
        # UI Controls
        self.interface_dropdown = None
        self.com_port_dropdown = None
        self.baudrate_field = None
        self.can_channel_field = None
        self.can_bitrate_field = None
        self.connect_button = None
        self.disconnect_button = None
        self.save_button = None
        self.save_status_text = None
        self.status_text = None
        
    def initialize(self):
        """Initialize the interface configuration module"""
        try:
            if not self.interface_manager.current_interface:
                self.interface_manager.initialize_interface()
            self.build_interface()
            # Update initial state
            self.update_connection_state(self.interface_manager.is_connected())
        except Exception as e:
            self.logger.error(f"Error initializing interface config module: {e}")
    
    def get_available_com_ports(self):
        """Get list of available COM ports"""
        try:
            ports = serial.tools.list_ports.comports()
            port_list = []
            for port in ports:
                port_list.append(ft.dropdown.Option(port.device, f"{port.device} - {port.description}"))
            return port_list
        except Exception as e:
            self.logger.error(f"Error getting COM ports: {e}")
            return [ft.dropdown.Option("COM1", "COM1")]
    
    def refresh_com_ports(self, e):
        """Refresh the COM ports dropdown"""
        try:
            self.com_port_dropdown.options = self.get_available_com_ports()
            self.page.update()
        except Exception as e:
            self.logger.error(f"Error refreshing COM ports: {e}")
    
    def save_configuration(self, e):
        """Save current configuration to app_config.json"""
        try:
            # Update config object with current UI values
            if self.config.can_config.interface == "usb_serial":
                self.config.can_config.com_port = self.com_port_dropdown.value
                self.config.can_config.serial_baudrate = int(self.baudrate_field.value)
            else:
                self.config.can_config.channel = self.can_channel_field.value
                self.config.can_config.bitrate = int(self.can_bitrate_field.value)
            
            self.config.can_config.interface = self.interface_dropdown.value
            
            # Save to JSON file
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     "config", "app_config.json")
            
            config_data = {
                "can": {
                    "interface": self.config.can_config.interface,
                    "channel": self.config.can_config.channel,
                    "bitrate": self.config.can_config.bitrate,
                    "timeout": self.config.can_config.timeout,
                    "com_port": self.config.can_config.com_port,
                    "serial_baudrate": self.config.can_config.serial_baudrate
                },
                "ui": {
                    "theme": getattr(self.config.ui_config, 'theme', 'light'),
                    "auto_refresh_rate": getattr(self.config.ui_config, 'auto_refresh_rate', 100),
                    "max_log_entries": getattr(self.config.ui_config, 'max_log_entries', 1000),
                    "graph_update_rate": getattr(self.config.ui_config, 'graph_update_rate', 500)
                },
                "network": {
                    "node_id": getattr(self.config.network_config, 'node_id', 1),
                    "heartbeat_period": getattr(self.config.network_config, 'heartbeat_period', 1000),
                    "sdo_timeout": getattr(self.config.network_config, 'sdo_timeout', 5.0),
                    "emergency_timeout": getattr(self.config.network_config, 'emergency_timeout', 2.0)
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info("Configuration saved successfully")
            
            # Show success message
            self.save_status_text.value = "✓ Saved!"
            self.save_status_text.color = ft.Colors.GREEN
            self.save_status_text.visible = True
            self.page.update()
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            
            # Show error message
            self.save_status_text.value = "✗ Error!"
            self.save_status_text.color = ft.Colors.RED
            self.save_status_text.visible = True
            self.page.update()
    
    def build_interface(self):
        """Build the interface configuration UI"""
        # Interface selection
        available_interfaces = self.interface_manager.get_available_interfaces()
        
        # Build options list without None values
        options = [ft.dropdown.Option("usb_serial", "USB Serial Converter")]
        if "socketcan" in available_interfaces:
            options.append(ft.dropdown.Option("socketcan", "SocketCAN (Linux)"))
        
        self.interface_dropdown = ft.Dropdown(
            label="Interface Type",
            value=self.config.can_config.interface,
            options=options,
            on_change=self.on_interface_change,
            width=200
        )
        
        # USB Serial configuration
        self.com_port_dropdown = ft.Dropdown(
            label="COM Port",
            value=self.config.can_config.com_port,
            options=self.get_available_com_ports(),
            width=200
        )
        
        self.refresh_ports_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Refresh COM Ports",
            on_click=self.refresh_com_ports
        )
        
        self.baudrate_field = ft.TextField(
            label="Baudrate",
            value=str(self.config.can_config.serial_baudrate),
            width=150
        )
        
        # SocketCAN configuration
        self.can_channel_field = ft.TextField(
            label="CAN Channel",
            value=self.config.can_config.channel,
            width=150
        )
        
        self.can_bitrate_field = ft.TextField(
            label="CAN Bitrate",
            value=str(self.config.can_config.bitrate),
            width=150
        )
        
        # Connection controls (moved to top level)
        self.connect_button = ft.ElevatedButton(
            text="Connect",
            icon=ft.Icons.LINK,
            on_click=self.on_connect_click,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE
        )
        
        self.disconnect_button = ft.ElevatedButton(
            text="Disconnect",
            icon=ft.Icons.LINK_OFF,
            on_click=self.on_disconnect_click,
            disabled=True,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE
        )
        
        # Save configuration button
        self.save_button = ft.ElevatedButton(
            text="Save Config",
            icon=ft.Icons.SAVE,
            on_click=self.save_configuration,
            bgcolor=ft.Colors.BLUE,
            color=ft.Colors.WHITE
        )
        
        # Save status message
        self.save_status_text = ft.Text(
            "",
            size=12,
            weight=ft.FontWeight.BOLD,
            visible=False
        )
        
        # Status display
        self.status_text = ft.Text(
            "Status: Disconnected",
            color=ft.Colors.RED,
            weight=ft.FontWeight.BOLD
        )
        
        # USB Serial configuration panel with integrated save button
        usb_serial_config = ft.Container(
            content=ft.Column([
                ft.Text("USB Serial Configuration", weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.com_port_dropdown,
                    self.refresh_ports_button,
                    self.baudrate_field,
                    self.save_button,
                    self.save_status_text
                ], alignment=ft.MainAxisAlignment.START)
            ]),
            visible=(self.config.can_config.interface == "usb_serial"),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=5
        )
        
        # SocketCAN configuration panel with integrated save button
        socketcan_config = ft.Container(
            content=ft.Column([
                ft.Text("SocketCAN Configuration", weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.can_channel_field,
                    self.can_bitrate_field,
                    self.save_button,
                    self.save_status_text
                ], alignment=ft.MainAxisAlignment.START)
            ]),
            visible=(self.config.can_config.interface == "socketcan"),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=5
        )
        
        # Build the complete interface with horizontal layout
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("CAN Interface Configuration", 
                           size=18, 
                           weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    
                    # Top level controls - Interface selection and Connection control in same row
                    ft.Container(
                        content=ft.Row([
                            # Interface selection
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Interface", weight=ft.FontWeight.BOLD, size=14),
                                    self.interface_dropdown
                                ]),
                                padding=10
                            ),
                            
                            # Connection controls embedded in same container
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Connection Control", weight=ft.FontWeight.BOLD, size=14),
                                    ft.Row([
                                        self.connect_button,
                                        self.disconnect_button
                                    ]),
                                    self.status_text
                                ]),
                                padding=10,
                                border=ft.border.all(1, ft.Colors.BLUE_300),
                                border_radius=5
                            )
                        ], alignment=ft.MainAxisAlignment.START),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_400),
                        border_radius=5
                    ),
                    
                    ft.Divider(),
                    
                    # Configuration panels
                    usb_serial_config,
                    socketcan_config
                    
                ]),
                padding=20
            )
        ]
        
        # Store references for visibility control
        self.usb_serial_config = usb_serial_config
        self.socketcan_config = socketcan_config
        
        self.expand = True
    
    def on_interface_change(self, e):
        """Handle interface type change"""
        try:
            interface_type = e.control.value
            
            # Update configuration
            self.config.can_config.interface = interface_type
            
            # Hide save status message when changing interface
            self.save_status_text.visible = False
            
            # Show/hide appropriate configuration panels
            self.usb_serial_config.visible = (interface_type == "usb_serial")
            self.socketcan_config.visible = (interface_type == "socketcan")
            
            # Update interface manager
            self.interface_manager.switch_interface(interface_type)
            
            # Reset connection state
            self.update_connection_state(False, False)
            
            self.page.update()
            
        except Exception as e:
            self.logger.error(f"Error changing interface: {e}")
    
    def on_connect_click(self, e):
        """Handle connect button click"""
        try:
            # Update configuration with current values
            if self.config.can_config.interface == "usb_serial":
                self.config.can_config.com_port = self.com_port_dropdown.value
                self.config.can_config.serial_baudrate = int(self.baudrate_field.value)
            else:
                self.config.can_config.channel = self.can_channel_field.value
                self.config.can_config.bitrate = int(self.can_bitrate_field.value)
            
            # Attempt connection (this will automatically notify all callbacks)
            if self.interface_manager.connect():
                self.update_connection_state(True)
                self.logger.info("Connected to CAN interface")
            else:
                self.status_text.value = "Status: Connection Failed"
                self.status_text.color = ft.Colors.RED
                self.page.update()
                
        except Exception as e:
            self.logger.error(f"Error connecting: {e}")
            self.status_text.value = f"Status: Error - {str(e)}"
            self.status_text.color = ft.Colors.RED
            self.page.update()
    
    def on_disconnect_click(self, e):
        """Handle disconnect button click"""
        try:
            # Disconnect (this will automatically notify all callbacks)
            self.interface_manager.disconnect()
            self.update_connection_state(False)
            self.logger.info("Disconnected from CAN interface")
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
    def update_connection_state(self, connected: bool):
        """Update UI based on connection state"""
        self.connect_button.disabled = connected
        self.disconnect_button.disabled = not connected
        
        if connected:
            self.status_text.value = "Status: Connected"
            self.status_text.color = ft.Colors.GREEN
        else:
            self.status_text.value = "Status: Disconnected"
            self.status_text.color = ft.Colors.RED
        
        self.page.update()
    
    def get_interface_manager(self) -> InterfaceManager:
        """Get the interface manager instance"""
        return self.interface_manager
    
    def set_connection_change_callback(self, callback):
        """Set callback for connection state changes"""
        self.connection_change_callback = callback
        
        self.page.update()
    
    def get_interface_manager(self) -> InterfaceManager:
        """Get the interface manager instance"""
        return self.interface_manager
    
    def set_connection_change_callback(self, callback):
        """Set callback for connection state changes"""
        self.connection_change_callback = callback
