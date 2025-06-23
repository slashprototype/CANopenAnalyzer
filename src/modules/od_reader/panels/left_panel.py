import flet as ft
from typing import Any, Dict
import os

class LeftPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        
        # UI Components
        self.file_path_text = ft.Text("No file selected", size=14)
        self.load_button = ft.ElevatedButton("Load OD XML", on_click=self.parent.load_od_file)
        self.status_text = ft.Text("Ready to load OD file", color=ft.Colors.BLUE)
        
        # Device info content reference
        self.device_info_content = ft.Text("Load an OD XML file to see device info", size=12, color=ft.Colors.GREY_600)
        
        # Summary card
        self.summary_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Summary", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text("Load an OD XML file to see summary", size=12, color=ft.Colors.GREY_600)
                ]),
                padding=12
            ),
            elevation=1
        )
    
    def initialize(self):
        """Initialize the left panel"""
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # File selection section
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("XML File Selection", size=14, weight=ft.FontWeight.BOLD),
                                ft.Divider(height=1),
                                self.load_button,
                                self.file_path_text,
                                self.status_text
                            ], spacing=8),
                            padding=12
                        ),
                        elevation=1
                    ),
                    
                    # Summary section
                    self.summary_card,
                    
                    # Device Information section
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Device Information", size=14, weight=ft.FontWeight.BOLD),
                                ft.Divider(height=1),
                                self.device_info_content
                            ], spacing=8),
                            padding=12
                        ),
                        elevation=1
                    ),
                    
                    # Save button
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
    
    def update_summary(self, summary: Dict[str, Any]):
        """Update summary information"""
        device_info = summary['device_info']
        
        # Update summary card
        summary_content = [
            ft.Text("Summary", size=14, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            ft.Text(f"📁 {os.path.basename(summary['xml_file'])}", size=11),
            ft.Text(f"📊 Objects: {summary['total_objects']}", size=11),
            ft.Text(f"🔧 Communication: {summary['communication_params']}", size=11),
            ft.Text(f"🏭 Manufacturer: {summary['manufacturer_params']}", size=11),
            ft.Text(f"⚙️ Device Profile: {summary['device_profile_params']}", size=11),
        ]
        
        self.summary_card.content = ft.Container(
            content=ft.Column(summary_content, spacing=6),
            padding=12
        )
        
        # Update device information
        if 'device_identity' in device_info:
            identity = device_info['device_identity']
            self.device_info_content = ft.Column([
                ft.Text(f"Vendor: {identity.get('vendorName', 'Unknown')}", size=11),
                ft.Text(f"Product: {identity.get('productName', 'Unknown')}", size=11),
                ft.Text(f"Version: {identity.get('productNumber', 'Unknown')}", size=11),
                ft.Text(f"Vendor ID: {identity.get('vendorNumber', 'Unknown')}", size=11),
            ], spacing=6)
            
            # Update device info in the card - fix index reference
            main_container = self.controls[0]  # The scrollable container
            device_card = main_container.content.controls[2]  # Third card in the scrollable column
            device_card.content.content.controls[2] = self.device_info_content
        else:
            self.device_info_content.value = "No device information available"
            self.device_info_content.color = ft.Colors.GREY_600
