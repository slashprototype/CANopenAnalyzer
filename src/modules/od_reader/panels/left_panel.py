import flet as ft
import os
from typing import Dict, Any

class LeftPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module

        self.file_path_text = ft.Text("No file selected", size=14)
        self.load_button = ft.ElevatedButton("Load OD.c", on_click=self.parent.load_od_file)
        self.status_text = ft.Text("Ready to load OD.c file", color=ft.Colors.BLUE)
        self.summary_text = ft.Text("No registers loaded", size=12, color=ft.Colors.GREY_600)

    def initialize(self):
        """Initialize the left panel"""
        # Create summary and device info cards
        self.summary_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Summary", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    self.summary_text
                ], spacing=8),
                padding=12
            ),
            elevation=1
        )
        
        self.device_info_content = ft.Text("No device information available", size=12, color=ft.Colors.GREY_600)
        device_info_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Device Information", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    self.device_info_content
                ], spacing=8),
                padding=12
            ),
            elevation=1
        )
        
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("OD.c File Selection", size=14, weight=ft.FontWeight.BOLD),
                                ft.Divider(height=1),
                                self.load_button,
                                self.file_path_text,
                                self.status_text
                            ], spacing=8),
                            padding=12
                        ),
                        elevation=1
                    ),
                    self.summary_card,
                    device_info_card,
                    ft.Container(
                        content=ft.ElevatedButton(
                            "Save Configuration",
                            icon=ft.Icons.SAVE,
                            on_click=self.parent.save_configuration,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.GREEN_600,
                                color=ft.Colors.WHITE
                            )
                        ),
                        margin=ft.margin.only(top=10)
                    )
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                expand=True
            )
        ]
        self.expand = True

    def update_file_info(self, filename: str):
        """Update file information"""
        self.file_path_text.value = f"File: {filename}"

    def update_status(self, message: str, color: str):
        """Update status message"""
        self.status_text.value = message
        self.status_text.color = color

    def update_summary(self, summary):
        """Update summary information - handles both int (register count) and dict (full summary)"""
        if isinstance(summary, int):
            # Handle simple register count from OD.c parser
            self.summary_text.value = f"📊 Total registers: {summary}"
            self.summary_text.color = ft.Colors.GREEN
            return
            
        if not summary:  # Handle None or empty summary
            self.status_text.value = "Warning: Invalid summary data"
            self.status_text.color = ft.Colors.ORANGE
            return
            
        device_info = summary.get('device_info', {})
        
        # Update summary card
        summary_content = [
            ft.Text("Summary", size=14, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            ft.Text(f"📁 {os.path.basename(summary.get('xml_file', 'Unknown'))}", size=11),
            ft.Text(f"📊 Objects: {summary.get('total_objects', 0)}", size=11),
            ft.Text(f"🔧 Communication: {summary.get('communication_params', 0)}", size=11),
            ft.Text(f"🏭 Manufacturer: {summary.get('manufacturer_params', 0)}", size=11),
            ft.Text(f"⚙️ Device Profile: {summary.get('device_profile_params', 0)}", size=11),
        ]
        
        self.summary_card.content = ft.Container(
            content=ft.Column(summary_content, spacing=6),
            padding=12
        )
        
        # Update device information
        if device_info and 'device_identity' in device_info:
            identity = device_info['device_identity']
            self.device_info_content = ft.Column([
                ft.Text(f"Vendor: {identity.get('vendorName', 'Unknown')}", size=11),
                ft.Text(f"Product: {identity.get('productName', 'Unknown')}", size=11),
                ft.Text(f"Version: {identity.get('productNumber', 'Unknown')}", size=11),
                ft.Text(f"Vendor ID: {identity.get('vendorNumber', 'Unknown')}", size=11),
            ], spacing=6)
            
            # Update device info in the card
            try:
                main_container = self.controls[0]  # The scrollable container
                device_card = main_container.content.controls[2]  # Third card in the scrollable column
                device_card.content.content.controls[2] = self.device_info_content
            except (IndexError, AttributeError) as e:
                print(f"Warning: Could not update device info card: {e}")
        else:
            self.device_info_content = ft.Text("No device information available", size=12, color=ft.Colors.GREY_600)
            try:
                main_container = self.controls[0]  # The scrollable container
                device_card = main_container.content.controls[2]  # Third card in the scrollable column
                device_card.content.content.controls[2] = self.device_info_content
            except (IndexError, AttributeError) as e:
                print(f"Warning: Could not update device info card: {e}")
                print(f"Warning: Could not update device info card: {e}")
