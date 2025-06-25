import flet as ft
import threading
import time
from typing import Any, List, Optional
from datetime import datetime

from interfaces import InterfaceManager, CANMessage

class MonitorModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: InterfaceManager = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.is_monitoring = False
        self.message_list = []
        self.message_table = None
        self.control_buttons = None
        # Use singleton instance
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        self.stats_controls = {}
        self.filter_node_id = None
        self.message_count = 0
        self.error_count = 0
        self.last_update_time = time.time()
        self.messages_since_last_update = 0
        
    def initialize(self):
        """Initialize the monitor module"""
        # Register for connection state changes
        self.interface_manager.add_connection_callback(self.update_connection_status)
        
        # Don't initialize interface manager here if one was provided
        if self.interface_manager and not self.interface_manager.current_interface:
            if not self.interface_manager.initialize_interface():
                self.logger.error("Failed to initialize CAN interface")
        
        self.message_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("COB-ID")),
                ft.DataColumn(ft.Text("Node")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Data")),
                ft.DataColumn(ft.Text("Length"))
            ],
            rows=[],
            heading_row_height=25,
            data_row_min_height=20,
            data_row_max_height=25,
        )
        
        self.build_interface()
    
    def build_interface(self):
        """Build the monitor interface"""
        # Control buttons (only monitoring controls, no connection)
        self.control_buttons = ft.Row([
            ft.ElevatedButton(
                "Start Monitor",
                icon=ft.Icons.PLAY_ARROW,
                on_click=self.start_monitoring,
                disabled=not self.interface_manager.is_connected()
            ),
            ft.ElevatedButton(
                "Stop Monitor",
                icon=ft.Icons.STOP,
                on_click=self.stop_monitoring,
                disabled=True
            ),
            ft.ElevatedButton(
                "Clear",
                icon=ft.Icons.CLEAR,
                on_click=self.clear_messages
            ),
            ft.Container(expand=True),  # Spacer
            ft.Text("Filter by Node ID:"),
            ft.TextField(
                width=100,
                hint_text="All",
                on_change=self.filter_messages
            )
        ])
        
        # Statistics
        self.stats_controls = {
            "msg_count": ft.Text("Messages: 0"),
            "error_count": ft.Text("Errors: 0"),
            "rate": ft.Text("Rate: 0 msg/s"),
            "interface_status": ft.Text("Status: Disconnected", color=ft.Colors.RED)
        }
        
        stats = ft.Row([
            self.stats_controls["msg_count"],
            self.stats_controls["error_count"],
            self.stats_controls["rate"],
            ft.Container(expand=True),
            self.stats_controls["interface_status"]
        ])
        
        # Build main layout
        self.controls = [
            ft.Container(
                content=self.control_buttons,
                padding=10
            ),
            ft.Container(
                content=stats,
                padding=10,
                bgcolor=ft.Colors.GREY_50
            ),
            ft.Container(
                content=ft.Column([
                    self.message_table
                ], scroll=ft.ScrollMode.AUTO),
                expand=True,
                padding=5
            )
        ]
        
        self.expand = True
    
    def start_monitoring(self, e):
        """Start CAN message monitoring"""
        try:
            if not self.interface_manager or not self.interface_manager.is_connected():
                self.logger.error("Cannot start monitoring - interface not connected")
                return
            
            # Clear existing messages for a clean start
            self.message_list.clear()
            self.message_table.rows.clear()
            self.message_count = 0
            self.error_count = 0
            self.messages_since_last_update = 0
            self.last_update_time = time.time()
            
            # Add message callback
            self.interface_manager.add_message_callback(self.on_message_received)
            
            # Start monitoring
            if self.interface_manager.start_monitoring():
                self.is_monitoring = True
                self.update_button_states()
                self.start_stats_update()
                self.logger.info("Started CAN message monitoring")
            else:
                self.logger.error("Failed to start monitoring")
            
            self.page.update()
        except Exception as ex:
            self.logger.error(f"Error starting monitoring: {ex}")
    
    def stop_monitoring(self, e):
        """Stop CAN message monitoring"""
        try:
            if self.interface_manager:
                self.interface_manager.stop_monitoring()
                # Remove message callback
                self.interface_manager.remove_message_callback(self.on_message_received)
            
            self.is_monitoring = False
            self.update_button_states()
            self.logger.info("Stopped CAN message monitoring")
            self.page.update()
        except Exception as ex:
            self.logger.error(f"Error stopping monitoring: {ex}")
    
    def clear_messages(self, e):
        """Clear message history"""
        self.message_list.clear()
        self.message_table.rows.clear()
        self.message_count = 0
        self.error_count = 0
        self.update_statistics()
        self.page.update()
        self.logger.info("Message history cleared")
    
    def filter_messages(self, e):
        """Filter messages by node ID"""
        try:
            filter_text = e.control.value.strip()
            if filter_text == "" or filter_text.lower() == "all":
                self.filter_node_id = None
            else:
                self.filter_node_id = int(filter_text)
            
            self.rebuild_message_table()
            self.logger.info(f"Message filter set to node ID: {self.filter_node_id}")
        except ValueError:
            self.logger.warning(f"Invalid node ID filter: {e.control.value}")
    
    def on_message_received(self, message: CANMessage):
        """Callback for received CAN messages"""
        try:
            # print(f"DEBUG: Monitor received message - COB-ID: 0x{message.cob_id:03X}, Node: {message.node_id}, Type: {message.message_type}, Data: {[hex(b) for b in message.data]}")
            
            self.message_list.append(message)
            self.message_count += 1
            self.messages_since_last_update += 1
            
            # Keep only last 1000 messages
            if len(self.message_list) > 1000:
                self.message_list.pop(0)
            
            # Add to table if it matches filter
            if self.filter_node_id is None or message.node_id == self.filter_node_id:
                # Format time
                time_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
                
                # Format data as hex string
                data_str = " ".join([f"{b:02X}" for b in message.data])
                
                # Create new row
                new_row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(time_str)),
                        ft.DataCell(ft.Text(f"0x{message.cob_id:03X}")),
                        ft.DataCell(ft.Text(str(message.node_id))),
                        ft.DataCell(ft.Text(message.message_type)),
                        ft.DataCell(ft.Text(data_str)),
                        ft.DataCell(ft.Text(str(message.length)))
                    ]
                )
                
                # Add to beginning of table (newest first)
                self.message_table.rows.insert(0, new_row)
                
                # Keep only last 100 rows in table for performance
                if len(self.message_table.rows) > 100:
                    self.message_table.rows.pop()
                
                # Update UI periodically (not every message for performance)
                if self.messages_since_last_update >= 10:
                    self.page.update()
                    self.messages_since_last_update = 0
                
        except Exception as ex:
            self.logger.error(f"Error processing received message: {ex}")
            self.error_count += 1
    
    def rebuild_message_table(self):
        """Rebuild message table with current filter"""
        self.message_table.rows.clear()
        
        filtered_messages = self.message_list
        if self.filter_node_id is not None:
            filtered_messages = [msg for msg in self.message_list if msg.node_id == self.filter_node_id]
        
        # Add last 100 messages to table (newest first)
        for message in reversed(filtered_messages[-100:]):
            time_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
            data_str = " ".join([f"{b:02X}" for b in message.data])
            
            new_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(time_str)),
                    ft.DataCell(ft.Text(f"0x{message.cob_id:03X}")),
                    ft.DataCell(ft.Text(str(message.node_id))),
                    ft.DataCell(ft.Text(message.message_type)),
                    ft.DataCell(ft.Text(data_str)),
                    ft.DataCell(ft.Text(str(message.length)))
                ]
            )
            
            self.message_table.rows.append(new_row)
        
        self.page.update()
    
    def start_stats_update(self):
        """Start statistics update thread"""
        def update_stats():
            while self.is_monitoring:
                self.update_statistics()
                time.sleep(1)  # Update every second
        
        stats_thread = threading.Thread(target=update_stats)
        stats_thread.daemon = True
        stats_thread.start()
    
    def update_statistics(self):
        """Update statistics display"""
        try:
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time
            
            if time_elapsed >= 1.0:  # Update rate every second
                rate = self.messages_since_last_update / time_elapsed
                self.stats_controls["rate"].value = f"Rate: {rate:.1f} msg/s"
                self.last_update_time = current_time
                self.messages_since_last_update = 0
            
            self.stats_controls["msg_count"].value = f"Messages: {self.message_count}"
            self.stats_controls["error_count"].value = f"Errors: {self.error_count}"
            
            # Update interface status
            if self.interface_manager.is_monitoring():
                self.stats_controls["interface_status"].value = "Status: Monitoring"
                self.stats_controls["interface_status"].color = ft.Colors.GREEN
            elif self.interface_manager.is_connected():
                self.stats_controls["interface_status"].value = "Status: Connected"
                self.stats_controls["interface_status"].color = ft.Colors.BLUE
            else:
                self.stats_controls["interface_status"].value = "Status: Disconnected"
                self.stats_controls["interface_status"].color = ft.Colors.RED
                
            self.page.update()
                
        except Exception as ex:
            self.logger.error(f"Error updating statistics: {ex}")
    
    def update_connection_status(self, connected: bool):
        """Update connection status display (called from interface manager)"""
        print(f"DEBUG: Monitor module - received connection status callback: {connected}")
        if connected:
            self.stats_controls["interface_status"].value = "Status: Connected"
            self.stats_controls["interface_status"].color = ft.Colors.BLUE
        else:
            self.stats_controls["interface_status"].value = "Status: Disconnected"
            self.stats_controls["interface_status"].color = ft.Colors.RED
            # Stop monitoring if disconnected
            if self.is_monitoring:
                self.stop_monitoring(None)
        
        self.update_button_states()
        self.page.update()
    
    def update_button_states(self):
        """Update button enabled/disabled states"""
        print(f"DEBUG: Monitor module - updating button states. Connected: {self.interface_manager.is_connected() if self.interface_manager else False}, Monitoring: {self.is_monitoring}")
        if self.control_buttons and len(self.control_buttons.controls) >= 2:
            start_button = self.control_buttons.controls[0]
            stop_button = self.control_buttons.controls[1]
            
            is_connected = self.interface_manager.is_connected() if self.interface_manager else False
            start_button.disabled = not is_connected or self.is_monitoring
            stop_button.disabled = not self.is_monitoring
            
            self.page.update()
    
    def set_interface_manager(self, interface_manager: InterfaceManager):
        """Set the interface manager from external module"""
        self.interface_manager = interface_manager
        self.update_button_states()
