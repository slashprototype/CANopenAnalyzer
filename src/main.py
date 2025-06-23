import flet as ft
import threading
from typing import Dict, Any

from gui.main_window import MainWindow
from config.app_config import AppConfig
from utils.logger import Logger
from modules.od_reader import ODReaderModule
from modules.variables_module import VariablesModule
from modules.monitor_module import MonitorModule
from modules.sync_module import SyncModule  # Import SyncModule

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
        
        # Create modules
        od_reader_module = ODReaderModule(page, self.config, self.logger)
        variables_module = VariablesModule(page, self.config, self.logger)  # Pass interface_manager
        monitor_module = MonitorModule(page, self.config, self.logger)  # Initialize MonitorModule
        sync_module = SyncModule(page, self.config, self.logger)  # Initialize SyncModule
        
        # Establish bidirectional cross-module references
        variables_module.set_od_reader_module(od_reader_module)
        od_reader_module.set_variables_module(variables_module)
        
        # Initialize modules
        od_reader_module.initialize()
        variables_module.initialize()
        monitor_module.initialize()
        sync_module.initialize()  # Initialize SyncModule
        
        # Define tab change handler BEFORE using it
        def on_tab_change(e):
            """Handle tab changes and cross-module communication"""
            selected_tab = e.control.selected_index
            
            # If switching to variables module, try to auto-load OD data
            if selected_tab == 2:  # Variables tab
                try:
                    variables_module.auto_load_from_od_reader()
                except Exception as ex:
                    self.logger.debug(f"Could not auto-load variables: {ex}")
            
            page.update()
        
        # Create tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Monitor",
                    content=monitor_module
                ),
                ft.Tab(
                    text="OD Reader",
                    content=od_reader_module
                ),
                ft.Tab(
                    text="Variables",
                    content=variables_module
                ),
                ft.Tab(
                    text="SYNC Master",  # Add SYNC tab
                    content=sync_module
                ),
                # ...other tabs...
            ],
            expand=1,
            on_change=on_tab_change  # Now this function is defined
        )
        
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
