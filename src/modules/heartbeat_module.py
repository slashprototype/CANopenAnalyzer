import flet as ft
from typing import Any

class HeartbeatModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        
    def initialize(self):
        """Initialize the heartbeat module"""
        self.controls = [
            ft.Container(
                content=ft.Text("Heartbeat Module - Coming Soon", size=20),
                alignment=ft.alignment.center,
                expand=True
            )
        ]
        self.expand = True
