import flet as ft
import threading
from typing import Dict, Any

from gui.main_window import MainWindow
from config.app_config import AppConfig
from utils.logger import Logger

class CANopenAnalyzer:
    def __init__(self):
        self.config = AppConfig()
        self.logger = Logger()
        self.main_window = None
        
    def main(self, page: ft.Page):
        """Main application entry point"""
        # Configure page properties
        page.title = "CANopen Analyzer"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1200
        page.window_height = 800
        page.window_min_width = 800
        page.window_min_height = 600
        
        # Initialize main window
        self.main_window = MainWindow(page, self.config, self.logger)
        self.main_window.initialize()
        
        # Add main window to page
        page.add(self.main_window)
        
        # Update page
        page.update()

def run_app():
    """Run the Flet application"""
    app = CANopenAnalyzer()
    ft.app(target=app.main, assets_dir="assets")

if __name__ == "__main__":
    run_app()
