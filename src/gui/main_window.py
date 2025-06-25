import flet as ft
from typing import Dict, Any

from modules.monitor_module import MonitorModule
from modules.variables_module import VariablesModule
from modules.nmt_module import NMTModule
from modules.heartbeat_module import HeartbeatModule
from modules.sync_module import SyncModule
from modules.od_reader.od_reader_module import ODReaderModule
from modules.graph_module import GraphModule
from modules.interface_config_module import InterfaceConfigModule
from interfaces.interface_manager import InterfaceManager

class MainWindow(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.modules: Dict[str, Any] = {}
        self.header_container = None
        self.interface_manager = None
        
    def initialize(self):
        """Initialize all modules and establish cross-references"""
        # Initialize singleton interface manager first
        self.interface_manager = InterfaceManager(self.config, self.logger)
        self.interface_manager.initialize_interface()
        
        # Register connection callback to update header color
        self.interface_manager.add_connection_callback(self.update_header_color)
        
        # Initialize all modules with proper dependencies
        self._initialize_modules()
        
        # Establish cross-module references
        self._setup_cross_references()
        
        # Initialize modules in proper order
        self._initialize_modules_in_order()
        
        # Build the interface
        self.build_interface()
    
    def _initialize_modules(self):
        """Create all module instances"""
        self.modules = {
            "interface": InterfaceConfigModule(self.page, self.config, self.logger, self.interface_manager),
            "monitor": MonitorModule(self.page, self.config, self.logger, self.interface_manager),
            "variables": VariablesModule(self.page, self.config, self.logger, self.interface_manager),
            "nmt": NMTModule(self.page, self.config, self.logger, self.interface_manager),
            "heartbeat": HeartbeatModule(self.page, self.config, self.logger),
            "sync": SyncModule(self.page, self.config, self.logger, self.interface_manager),
            "od_reader": ODReaderModule(self.page, self.config, self.logger),
            "graphs": GraphModule(self.page, self.config, self.logger)
        }
    
    def _setup_cross_references(self):
        """Establish bidirectional cross-module references"""
        # Variables <-> OD Reader bidirectional reference
        self.modules["variables"].set_od_reader_module(self.modules["od_reader"])
        self.modules["od_reader"].set_variables_module(self.modules["variables"])
        
        # Add other cross-references as needed
        # Example: self.modules["graphs"].set_variables_module(self.modules["variables"])
    
    def _initialize_modules_in_order(self):
        """Initialize modules in the correct order to handle dependencies"""
        # Initialize interface first
        self.modules["interface"].initialize()
        
        # Initialize OD reader (no dependencies)
        self.modules["od_reader"].initialize()
        
        # Initialize modules that depend on interface manager
        interface_dependent_modules = ["variables", "nmt", "sync"]
        for module_name in interface_dependent_modules:
            self.modules[module_name].initialize()
        
        # Initialize monitor module last (after interface is ready)
        self.modules["monitor"].initialize()
        
        # Initialize remaining modules
        remaining_modules = ["heartbeat", "graphs"]
        for module_name in remaining_modules:
            self.modules[module_name].initialize()
    
    def build_interface(self):
        """Build the main interface"""
        # Define tab change handler
        def on_tab_change(e):
            """Handle tab changes and cross-module communication"""
            selected_tab = e.control.selected_index
            
            # Auto-load OD data when switching to variables tab
            if selected_tab == 2:  # Variables tab
                try:
                    self.modules["variables"].auto_load_from_od_reader()
                except Exception as ex:
                    self.logger.debug(f"Could not auto-load variables: {ex}")
            
            self.page.update()
        
        # Create tabs for each module
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Interface",
                    icon=ft.Icons.SETTINGS_INPUT_COMPONENT,
                    content=self.modules["interface"]
                ),
                ft.Tab(
                    text="Monitor",
                    icon=ft.Icons.MONITOR,
                    content=self.modules["monitor"]
                ),
                ft.Tab(
                    text="Variables",
                    icon=ft.Icons.SETTINGS,
                    content=self.modules["variables"]
                ),
                ft.Tab(
                    text="NMT Control",
                    icon=ft.Icons.NETWORK_CHECK,
                    content=self.modules["nmt"]
                ),
                ft.Tab(
                    text="Heartbeat",
                    icon=ft.Icons.FAVORITE,
                    content=self.modules["heartbeat"]
                ),
                ft.Tab(
                    text="SYNC Master",
                    icon=ft.Icons.SYNC,
                    content=self.modules["sync"]
                ),
                ft.Tab(
                    text="OD Reader",
                    icon=ft.Icons.DESCRIPTION,
                    content=self.modules["od_reader"]
                ),
                ft.Tab(
                    text="Graphs",
                    icon=ft.Icons.SHOW_CHART,
                    content=self.modules["graphs"]
                )
            ],
            expand=1,
            on_change=on_tab_change
        )
        
        # Create status bar
        status_bar = ft.Container(
            content=ft.Row([
                ft.Text("Status: Ready", size=12),
                ft.Text("CANopen Analyzer v1.0", size=12),
            ]),
            bgcolor=ft.Colors.GREY_100,
            padding=10,
            height=40
        )
        
        # Create header container with reference for color updates
        self.header_container = ft.Container(
            content=ft.Row([
                ft.Text(
                    "CANopen Analyzer", 
                    size=20, 
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.INFO,
                    tooltip="About",
                    on_click=self.show_about
                )
            ]),
            bgcolor=ft.Colors.BLUE_50,
            padding=10
        )
        
        # Add components to main window
        self.controls = [
            self.header_container,
            tabs,
            status_bar
        ]
        
        self.expand = True
    
    def update_header_color(self, connected: bool):
        """Update header background color based on connection status"""
        if self.header_container:
            if connected:
                self.header_container.bgcolor = ft.Colors.LIGHT_GREEN_100
            else:
                self.header_container.bgcolor = ft.Colors.BLUE_50
            
            self.page.update()
    
    def show_about(self, e):
        """Show about dialog"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("About CANopen Analyzer"),
            content=ft.Text(
                "CANopen Analyzer v1.0\n\n"
                "A comprehensive tool for CANopen network analysis and debugging.\n\n"
                "Features:\n"
                "• Multiple CAN interface support\n"
                "• Real-time message monitoring\n"
                "• Variable reading/writing\n"
                "• NMT control\n"
                "• Heartbeat monitoring\n"
                "• Object Dictionary reading\n"
                "• Data visualization"
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
