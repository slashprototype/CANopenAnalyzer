import flet as ft
from typing import Any
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
        self.com_port_field = None
        self.baudrate_field = None
        self.can_channel_field = None
        self.can_bitrate_field = None
        self.connect_button = None
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
        self.com_port_field = ft.TextField(
            label="COM Port",
            value=self.config.can_config.com_port,
            width=150
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
          # Connection controls
        self.connect_button = ft.ElevatedButton(
            text="Connect",
            icon=ft.Icons.LINK,
            on_click=self.on_connect_click
        )
        
        self.disconnect_button = ft.ElevatedButton(
            text="Disconnect",
            icon=ft.Icons.LINK_OFF,
            on_click=self.on_disconnect_click,
            disabled=True
        )
        
        # Status display
        self.status_text = ft.Text(
            "Status: Disconnected",
            color=ft.Colors.RED
        )
        
        # USB Serial configuration panel
        usb_serial_config = ft.Container(
            content=ft.Column([
                ft.Text("USB Serial Configuration", weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.com_port_field,
                    self.baudrate_field
                ])
            ]),
            visible=(self.config.can_config.interface == "usb_serial"),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=5
        )
        
        # SocketCAN configuration panel
        socketcan_config = ft.Container(
            content=ft.Column([
                ft.Text("SocketCAN Configuration", weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.can_channel_field,
                    self.can_bitrate_field
                ])
            ]),
            visible=(self.config.can_config.interface == "socketcan"),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=5
        )
        
        # Build the complete interface
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("CAN Interface Configuration", 
                           size=18, 
                           weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    
                    # Interface selection
                    ft.Row([
                        self.interface_dropdown
                    ]),
                    
                    # Configuration panels
                    usb_serial_config,
                    socketcan_config,
                      ft.Divider(),
                    
                    # Connection controls
                    ft.Row([
                        self.connect_button,
                        self.disconnect_button
                    ]),
                    
                    # Status
                    self.status_text,
                    
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
                self.config.can_config.com_port = self.com_port_field.value
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
        return self.interface_manager
    
    def set_connection_change_callback(self, callback):
        """Set callback for connection state changes"""
        self.connection_change_callback = callback
