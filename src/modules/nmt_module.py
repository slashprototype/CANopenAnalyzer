import flet as ft
from typing import Any, Optional
from interfaces.interface_manager import InterfaceManager

class NMTModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: Optional[InterfaceManager] = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        
        # NMT Command Codes (CANopen standard)
        self.NMT_COMMANDS = {
            "START_REMOTE_NODE": 0x01,
            "STOP_REMOTE_NODE": 0x02,
            "ENTER_PRE_OPERATIONAL": 0x80,
            "RESET_NODE": 0x81,
            "RESET_COMMUNICATION": 0x82
        }
        
        # NMT State descriptions
        self.NMT_STATES = {
            0x00: "Boot-up",
            0x04: "Stopped",
            0x05: "Operational", 
            0x7F: "Pre-operational"
        }
        
        # UI Controls
        self.node_id_field = None
        self.command_dropdown = None
        self.send_button = None
        self.status_text = None
        self.log_container = None
        self.detected_nodes_list = None
        
    def initialize(self):
        """Initialize the NMT module"""
        self.build_interface()
        
        # Register for message callbacks to detect nodes
        if self.interface_manager:
            self.interface_manager.add_message_callback(self.on_message_received)
        
    def build_interface(self):
        """Build the NMT control interface"""
        
        # Node ID input
        self.node_id_field = ft.TextField(
            label="Node ID",
            hint_text="1-127 (0 for broadcast)",
            value="0",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Command selection dropdown
        self.command_dropdown = ft.Dropdown(
            label="NMT Command",
            width=250,
            options=[
                ft.dropdown.Option("START_REMOTE_NODE", "Start Remote Node"),
                ft.dropdown.Option("STOP_REMOTE_NODE", "Stop Remote Node"),
                ft.dropdown.Option("ENTER_PRE_OPERATIONAL", "Enter Pre-operational"),
                ft.dropdown.Option("RESET_NODE", "Reset Node"),
                ft.dropdown.Option("RESET_COMMUNICATION", "Reset Communication"),
            ],
            value="START_REMOTE_NODE"
        )
        
        # Send button
        self.send_button = ft.ElevatedButton(
            "Send NMT Command",
            icon=ft.Icons.SEND,
            on_click=self.send_nmt_command,
            disabled=True
        )
        
        # Status text
        self.status_text = ft.Text(
            "Interface not connected",
            color=ft.Colors.RED,
            weight=ft.FontWeight.BOLD
        )
        
        # Update status based on connection
        self.update_connection_status()
        
        # Quick action buttons
        quick_actions = ft.Row([
            ft.ElevatedButton(
                "Start All",
                icon=ft.Icons.PLAY_ARROW,
                on_click=lambda e: self.send_broadcast_command("START_REMOTE_NODE"),
                bgcolor=ft.Colors.GREEN_100
            ),
            ft.ElevatedButton(
                "Stop All", 
                icon=ft.Icons.STOP,
                on_click=lambda e: self.send_broadcast_command("STOP_REMOTE_NODE"),
                bgcolor=ft.Colors.RED_100
            ),
            ft.ElevatedButton(
                "Pre-op All",
                icon=ft.Icons.PAUSE,
                on_click=lambda e: self.send_broadcast_command("ENTER_PRE_OPERATIONAL"),
                bgcolor=ft.Colors.ORANGE_100
            ),
            ft.ElevatedButton(
                "Reset All",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: self.send_broadcast_command("RESET_NODE"),
                bgcolor=ft.Colors.PURPLE_100
            )
        ])
        
        # Command log
        self.log_container = ft.Column(
            height=200,
            scroll=ft.ScrollMode.ALWAYS,
            controls=[
                ft.Text("NMT Command Log:", weight=ft.FontWeight.BOLD),
                ft.Text("Ready to send NMT commands...", color=ft.Colors.GREY)
            ]
        )
        
        # Detected nodes list
        self.detected_nodes_list = ft.Column(
            height=150,
            scroll=ft.ScrollMode.ALWAYS,
            controls=[
                ft.Text("Detected Nodes:", weight=ft.FontWeight.BOLD),
                ft.Text("No nodes detected yet", color=ft.Colors.GREY)
            ]
        )
        
        # Main interface layout
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Header
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.NETWORK_CHECK, size=30),
                            ft.Text("NMT Network Management", size=24, weight=ft.FontWeight.BOLD),
                        ]),
                        padding=10
                    ),
                    
                    ft.Divider(),
                    
                    # Status row
                    ft.Row([
                        ft.Text("Connection Status:", weight=ft.FontWeight.BOLD),
                        self.status_text
                    ]),
                    
                    ft.Divider(),
                    
                    # Command controls
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Individual Node Control:", weight=ft.FontWeight.BOLD),
                            ft.Row([
                                self.node_id_field,
                                self.command_dropdown,
                                self.send_button
                            ]),
                            
                            ft.Container(height=10),
                            
                            ft.Text("Broadcast Commands:", weight=ft.FontWeight.BOLD),
                            quick_actions,
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=10
                    ),
                    
                    ft.Container(height=10),
                    
                    # Two column layout for logs and nodes
                    ft.Row([
                        # Command log
                        ft.Container(
                            content=self.log_container,
                            bgcolor=ft.Colors.GREY_50,
                            border_radius=10,
                            padding=10,
                            expand=True
                        ),
                        
                        ft.Container(width=10),
                        
                        # Detected nodes
                        ft.Container(
                            content=self.detected_nodes_list,
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=10,
                            padding=10,
                            expand=True
                        )
                    ], expand=True)
                    
                ]),
                padding=20
            )
        ]
        
        self.expand = True
        
        # Register for connection status updates
        if self.interface_manager:
            self.interface_manager.add_connection_callback(self.on_connection_change)
    
    def update_connection_status(self):
        """Update UI based on connection status"""
        if self.interface_manager and self.interface_manager.is_connected():
            self.status_text.value = "Connected and ready"
            self.status_text.color = ft.Colors.GREEN
            self.send_button.disabled = False
        else:
            self.status_text.value = "Interface not connected"
            self.status_text.color = ft.Colors.RED
            self.send_button.disabled = True
        
        if self.page:
            self.page.update()
    
    def on_connection_change(self, connected: bool):
        """Handle connection state changes"""
        self.update_connection_status()
    
    def send_nmt_command(self, e):
        """Send individual NMT command"""
        try:
            node_id = int(self.node_id_field.value)
            command_key = self.command_dropdown.value
            
            if node_id < 0 or node_id > 127:
                self.add_log_entry("Error: Node ID must be between 0-127", ft.Colors.RED)
                return
            
            self.send_nmt_command_internal(command_key, node_id)
            
        except ValueError:
            self.add_log_entry("Error: Invalid Node ID", ft.Colors.RED)
        except Exception as ex:
            self.add_log_entry(f"Error: {str(ex)}", ft.Colors.RED)
    
    def send_broadcast_command(self, command_key: str):
        """Send broadcast NMT command (node ID = 0)"""
        self.send_nmt_command_internal(command_key, 0)
    
    def send_nmt_command_internal(self, command_key: str, node_id: int):
        """Internal method to send NMT command"""
        try:
            if not self.interface_manager or not self.interface_manager.is_connected():
                self.add_log_entry("Error: Interface not connected", ft.Colors.RED)
                return
            
            command_code = self.NMT_COMMANDS.get(command_key)
            if command_code is None:
                self.add_log_entry(f"Error: Unknown command {command_key}", ft.Colors.RED)
                return
            
            # Send NMT command through interface manager
            success = self.interface_manager.send_nmt_message(command_code, node_id)
            
            if success:
                target = "All nodes" if node_id == 0 else f"Node {node_id}"
                command_name = command_key.replace("_", " ").title()
                self.add_log_entry(
                    f"✓ Sent {command_name} to {target} (0x{command_code:02X})", 
                    ft.Colors.GREEN
                )
                self.logger.info(f"NMT command sent: {command_name} to {target}")
            else:
                self.add_log_entry("✗ Failed to send NMT command", ft.Colors.RED)
                self.logger.error("Failed to send NMT command")
                
        except Exception as ex:
            self.add_log_entry(f"Error: {str(ex)}", ft.Colors.RED)
            self.logger.error(f"Error sending NMT command: {ex}")
    
    def on_message_received(self, message):
        """Handle received CAN messages to detect node states"""
        try:
            # Check for NMT bootup messages (COB-ID 0x700 + Node ID)
            if 0x700 <= message.cob_id <= 0x77F:
                node_id = message.cob_id - 0x700
                if len(message.data) == 1:
                    state_code = message.data[0]
                    state_name = self.NMT_STATES.get(state_code, f"Unknown (0x{state_code:02X})")
                    
                    self.update_detected_node(node_id, state_name)
                    self.add_log_entry(
                        f"Node {node_id} state: {state_name}", 
                        ft.Colors.BLUE
                    )
                    
        except Exception as ex:
            self.logger.debug(f"Error processing message for NMT: {ex}")
    
    def update_detected_node(self, node_id: int, state: str):
        """Update the detected nodes list"""
        try:
            # Find if node already exists in list
            node_found = False
            for control in self.detected_nodes_list.controls[1:]:  # Skip header
                if hasattr(control, 'data') and control.data == node_id:
                    control.value = f"Node {node_id}: {state}"
                    node_found = True
                    break
            
            # If node not found, add it
            if not node_found:
                # Remove "No nodes detected" message if it exists
                if len(self.detected_nodes_list.controls) == 2:
                    if "No nodes detected" in self.detected_nodes_list.controls[1].value:
                        self.detected_nodes_list.controls.pop()
                
                # Add new node entry
                node_text = ft.Text(f"Node {node_id}: {state}")
                node_text.data = node_id  # Store node ID for identification
                self.detected_nodes_list.controls.append(node_text)
            
            if self.page:
                self.page.update()
                
        except Exception as ex:
            self.logger.debug(f"Error updating detected nodes: {ex}")
    
    def add_log_entry(self, message: str, color=ft.Colors.BLACK):
        """Add entry to command log"""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = ft.Text(f"[{timestamp}] {message}", color=color, size=12)
            
            self.log_container.controls.append(log_entry)
            
            # Keep only last 20 entries (plus header)
            if len(self.log_container.controls) > 21:
                self.log_container.controls.pop(1)  # Remove oldest (skip header)
            
            if self.page:
                self.page.update()
                
        except Exception as ex:
            self.logger.debug(f"Error adding log entry: {ex}")
            self.log_container.controls.pop(1)  # Remove oldest (skip header)
            
            if self.page:
                self.page.update()
                
        except Exception as ex:
            self.logger.debug(f"Error adding log entry: {ex}")
