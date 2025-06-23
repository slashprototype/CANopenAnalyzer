"""
SYNC Module - Manages SYNC message transmission as master
"""

import flet as ft
import threading
import time
from typing import Optional, Any
from config.app_config import AppConfig
from utils.logger import Logger

class SyncModule(ft.Column):
    """Module for managing SYNC message transmission"""
    
    def __init__(self, page: ft.Page, config: AppConfig, logger: Logger, interface_manager=None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.interface_manager = interface_manager
        
        # SYNC service state
        self.is_sync_active = False
        self.sync_thread: Optional[threading.Thread] = None
        self.sync_interval = 100  # Default 100ms
        self.sync_counter = 0
        self.max_counter = 0  # Default max counter (0-240, then wraps to 1)
        self.sync_cob_id = 0x80  # Default SYNC COB-ID
        
        # GUI controls
        self.status_text = None
        self.interval_field = None
        self.cob_id_field = None
        self.max_counter_field = None
        self.start_stop_button = None
        self.counter_display = None
        self.stats_text = None
        self.reset_button = None
        
        # Statistics
        self.sync_count = 0
        self.start_time = None
        self.last_send_time = None
        self.failed_sends = 0
        
    def initialize(self):
        """Initialize the SYNC module"""
        self.logger.info("Initializing SYNC module")
        self.build_gui()
        
    def build_gui(self):
        """Build the SYNC module GUI"""
        # Title and status
        title_row = ft.Row([
            ft.Icon(ft.Icons.SYNC, size=24),
            ft.Text("SYNC Master Service", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            self.create_status_indicator()
        ])
        
        # Configuration section
        config_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("SYNC Configuration", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    
                    # SYNC COB-ID
                    ft.Row([
                        ft.Text("SYNC COB-ID:", width=120),
                        ft.TextField(
                            ref=ft.Ref[ft.TextField](),
                            value=f"0x{self.sync_cob_id:03X}",
                            width=120,
                            hint_text="0x080",
                            on_change=self.on_cob_id_change
                        ),
                        ft.Text("(Hex format, e.g., 0x080)")
                    ]),
                    
                    # SYNC Interval
                    ft.Row([
                        ft.Text("Interval (ms):", width=120),
                        ft.TextField(
                            ref=ft.Ref[ft.TextField](),
                            value=str(self.sync_interval),
                            width=120,
                            hint_text="100",
                            on_change=self.on_interval_change
                        ),
                        ft.Text("(1-10000 ms)")
                    ]),
                    
                    # Max Counter
                    ft.Row([
                        ft.Text("Max Counter:", width=120),
                        ft.TextField(
                            ref=ft.Ref[ft.TextField](),
                            value=str(self.max_counter),
                            width=120,
                            hint_text="240",
                            on_change=self.on_max_counter_change
                        ),
                        ft.Text("(0=no counter, 1-240)")
                    ]),
                ]),
                padding=15
            )
        )
        
        # Store references to controls
        self.cob_id_field = config_card.content.content.controls[2].controls[1]
        self.interval_field = config_card.content.content.controls[3].controls[1]
        self.max_counter_field = config_card.content.content.controls[4].controls[1]
        
        # Control section
        control_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("SYNC Control", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    
                    # Start/Stop button
                    ft.Row([
                        ft.ElevatedButton(
                            text="Start SYNC",
                            icon=ft.Icons.PLAY_ARROW,
                            on_click=self.toggle_sync_service,
                            ref=ft.Ref[ft.ElevatedButton]()
                        ),
                        ft.Container(width=20),
                        ft.ElevatedButton(
                            text="Reset Counter",
                            icon=ft.Icons.REFRESH,
                            on_click=self.reset_counter,
                            disabled=False,
                            ref=ft.Ref[ft.ElevatedButton]()
                        )
                    ]),
                    
                    ft.Container(height=10),
                    
                    # Current counter display
                    ft.Row([
                        ft.Text("Current Counter:", weight=ft.FontWeight.BOLD),
                        ft.Text(
                            str(self.sync_counter),
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE,
                            ref=ft.Ref[ft.Text]()
                        )
                    ]),
                ]),
                padding=15
            )
        )
        
        # Store references
        self.start_stop_button = control_card.content.content.controls[2].controls[0]
        self.reset_button = control_card.content.content.controls[2].controls[2]
        self.counter_display = control_card.content.content.controls[4].controls[1]
        
        # Statistics section
        stats_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Statistics", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text(
                        "SYNC messages sent: 0\nFailed sends: 0\nUptime: 0 seconds\nAvg rate: 0.0 msg/s\nLast interval: N/A",
                        ref=ft.Ref[ft.Text]()
                    )
                ]),
                padding=15
            )
        )
        
        self.stats_text = stats_card.content.content.controls[2]
        
        # Main layout
        self.controls = [
            title_row,
            ft.Container(height=10),
            
            # Two column layout for desktop
            ft.Row([
                ft.Column([
                    config_card,
                    control_card
                ], width=400),
                ft.Container(width=20),
                ft.Column([
                    stats_card,
                    # Future: Add message log or timing charts
                ], expand=True)
            ], expand=True)
        ]
        
        self.expand = True
        
    def create_status_indicator(self):
        """Create status indicator"""
        self.status_text = ft.Text(
            "Stopped",
            color=ft.Colors.RED,
            weight=ft.FontWeight.BOLD
        )
        
        return ft.Row([
            ft.Icon(ft.Icons.CIRCLE, size=12, color=ft.Colors.RED),
            self.status_text
        ])
    
    def on_cob_id_change(self, e):
        """Handle COB-ID change"""
        try:
            value = e.control.value.strip()
            if value.startswith("0x") or value.startswith("0X"):
                cob_id = int(value, 16)
            else:
                cob_id = int(value)
                
            if 0 <= cob_id <= 0x7FF:
                self.sync_cob_id = cob_id
                self.logger.debug(f"SYNC COB-ID changed to: 0x{cob_id:03X}")
            else:
                raise ValueError("COB-ID out of range")
                
        except ValueError:
            # Reset to previous valid value
            e.control.value = f"0x{self.sync_cob_id:03X}"
            self.page.update()
    
    def on_interval_change(self, e):
        """Handle interval change"""
        try:
            interval = int(e.control.value)
            if 1 <= interval <= 10000:
                self.sync_interval = interval
                self.logger.debug(f"SYNC interval changed to: {interval}ms")
            else:
                raise ValueError("Interval out of range")
        except ValueError:
            # Reset to previous valid value
            e.control.value = str(self.sync_interval)
            self.page.update()
    
    def on_max_counter_change(self, e):
        """Handle max counter change"""
        try:
            max_counter = int(e.control.value)
            if 0 <= max_counter <= 240:
                self.max_counter = max_counter
                self.logger.debug(f"SYNC max counter changed to: {max_counter}")
            else:
                raise ValueError("Max counter out of range")
        except ValueError:
            # Reset to previous valid value
            e.control.value = str(self.max_counter)
            self.page.update()
    
    def toggle_sync_service(self, e):
        """Toggle SYNC service on/off"""
        if not self.is_sync_active:
            self.start_sync_service()
        else:
            self.stop_sync_service()
    
    def start_sync_service(self):
        """Start the SYNC service"""
        # Check if interface is connected
        if not self.interface_manager or not self.interface_manager.is_connected():
            self.show_error("Interface not connected. Please connect to CAN interface first.")
            return
        
        self.is_sync_active = True
        self.sync_count = 0
        self.failed_sends = 0
        self.start_time = time.time()
        self.last_send_time = None
        
        # Update GUI
        self.start_stop_button.text = "Stop SYNC"
        self.start_stop_button.icon = ft.Icons.STOP
        self.status_text.value = "Running"
        self.status_text.color = ft.Colors.GREEN
        
        # Update status indicator
        self.controls[0].controls[3].controls[0].color = ft.Colors.GREEN
        
        # Disable configuration during operation
        self.cob_id_field.disabled = True
        self.interval_field.disabled = True
        self.max_counter_field.disabled = True
        
        # Start SYNC thread
        self.sync_thread = threading.Thread(target=self.sync_worker, daemon=True)
        self.sync_thread.start()
        
        self.logger.info(f"SYNC service started - COB-ID: 0x{self.sync_cob_id:03X}, Interval: {self.sync_interval}ms")
        self.page.update()
    
    def stop_sync_service(self):
        """Stop the SYNC service"""
        self.is_sync_active = False
        
        # Update GUI
        self.start_stop_button.text = "Start SYNC"
        self.start_stop_button.icon = ft.Icons.PLAY_ARROW
        self.status_text.value = "Stopped"
        self.status_text.color = ft.Colors.RED
        
        # Update status indicator
        self.controls[0].controls[3].controls[0].color = ft.Colors.RED
        
        # Enable configuration
        self.cob_id_field.disabled = False
        self.interval_field.disabled = False
        self.max_counter_field.disabled = False
        
        self.logger.info("SYNC service stopped")
        self.page.update()
    
    def sync_worker(self):
        """Worker thread for sending SYNC messages"""
        while self.is_sync_active:
            try:
                current_time = time.time()
                
                # Send SYNC message through interface manager
                success = False
                if self.interface_manager and self.interface_manager.is_connected():
                    if self.max_counter > 0:
                        success = self.interface_manager.send_sync_message(self.sync_cob_id, self.sync_counter)
                    else:
                        success = self.interface_manager.send_sync_message(self.sync_cob_id, None)
                else:
                    self.logger.warning("Interface disconnected during SYNC transmission")
                    self.stop_sync_service()
                    break
                
                if success:
                    self.sync_count += 1
                    self.logger.debug(f"SYNC sent - COB-ID: 0x{self.sync_cob_id:03X}, Counter: {self.sync_counter if self.max_counter > 0 else 'None'}")
                    
                    # Update counter
                    self.update_sync_counter()
                else:
                    self.failed_sends += 1
                    self.logger.warning(f"Failed to send SYNC message - COB-ID: 0x{self.sync_cob_id:03X}")
                
                # Calculate actual interval for statistics
                if self.last_send_time:
                    actual_interval = (current_time - self.last_send_time) * 1000
                else:
                    actual_interval = self.sync_interval
                
                self.last_send_time = current_time
                
                # Update statistics
                self.update_statistics(actual_interval)
                
                # Wait for next interval
                time.sleep(self.sync_interval / 1000.0)
                
            except Exception as e:
                self.logger.error(f"Error in SYNC worker: {e}")
                self.failed_sends += 1
                break
        
        # If we exit the loop due to error, stop the service
        if self.is_sync_active:
            self.stop_sync_service()
    
    def prepare_sync_message(self) -> dict:
        """Prepare SYNC message data"""
        if self.max_counter > 0:
            data = [self.sync_counter]
        else:
            data = []
            
        return {
            'cob_id': self.sync_cob_id,
            'data': data,
            'is_extended': False
        }
    
    def update_sync_counter(self):
        """Update SYNC counter value"""
        if self.max_counter > 0:
            self.sync_counter += 1
            if self.sync_counter > self.max_counter:
                self.sync_counter = 1  # Wrap to 1, not 0
        
        # Update GUI counter display (thread-safe update)
        def update_gui():
            if self.counter_display:
                self.counter_display.value = str(self.sync_counter)
                self.page.update()
        
        # Schedule GUI update on main thread
        try:
            self.page.run_thread(update_gui)
        except:
            # Fallback if run_thread is not available
            pass
    
    def reset_counter(self, e):
        """Reset SYNC counter to 0"""
        self.sync_counter = 0
        if self.counter_display:
            self.counter_display.value = str(self.sync_counter)
            self.page.update()
        self.logger.info("SYNC counter reset")
    
    def update_statistics(self, actual_interval=None):
        """Update statistics display"""
        if not self.stats_text or not self.start_time:
            return
            
        uptime = time.time() - self.start_time
        avg_rate = self.sync_count / uptime if uptime > 0 else 0
        
        interval_text = f"{actual_interval:.1f} ms" if actual_interval else "N/A"
        
        stats_text = (
            f"SYNC messages sent: {self.sync_count}\n"
            f"Failed sends: {self.failed_sends}\n"
            f"Uptime: {uptime:.1f} seconds\n"
            f"Avg rate: {avg_rate:.1f} msg/s\n"
            f"Last interval: {interval_text}"
        )
        
        # Thread-safe GUI update
        def update_stats_gui():
            self.stats_text.value = stats_text
            self.page.update()
        
        try:
            self.page.run_thread(update_stats_gui)
        except:
            # Fallback if run_thread is not available
            self.stats_text.value = stats_text
    
    def show_error(self, message: str):
        """Show error dialog"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close_dialog)],
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def cleanup(self):
        """Cleanup when module is destroyed"""
        if self.is_sync_active:
            self.stop_sync_service()
