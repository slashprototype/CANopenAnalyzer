import flet as ft
from typing import Dict, Any

from modules.monitor_module import MonitorModule
from modules.variables_module import VariablesModule
from modules.nmt_module import NMTModule
from modules.heartbeat_module import HeartbeatModule
from modules.od_reader_module import ODReaderModule
from modules.graph_module import GraphModule
from modules.interface_config_module import InterfaceConfigModule
from interfaces.interface_manager import InterfaceManager  # Import InterfaceManager

class MainWindow(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.modules: Dict[str, Any] = {}
        
    def initialize(self):
        """Initialize all modules"""
        # Initialize singleton interface manager first
        interface_manager = InterfaceManager(self.config, self.logger)
        interface_manager.initialize_interface()
        
        # Initialize interface module with singleton
        interface_module = InterfaceConfigModule(self.page, self.config, self.logger, interface_manager)
        interface_module.initialize()
        
        # Initialize modules using singleton interface manager
        self.modules = {
            "interface": interface_module,
            "monitor": MonitorModule(self.page, self.config, self.logger, interface_manager),
            "variables": VariablesModule(self.page, self.config, self.logger),
            "nmt": NMTModule(self.page, self.config, self.logger),
            "heartbeat": HeartbeatModule(self.page, self.config, self.logger),
            "od_reader": ODReaderModule(self.page, self.config, self.logger),
            "graphs": GraphModule(self.page, self.config, self.logger)
        }
        
        # Initialize remaining modules
        for name, module in self.modules.items():
            if name not in ["interface", "monitor"]:  # interface and monitor already initialized
                module.initialize()
        
        # Initialize monitor module after interface
        self.modules["monitor"].initialize()
            
        # Build the interface
        self.build_interface()
    
    def build_interface(self):
        """Build the main interface"""
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
            expand=1
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
        
        # Add components to main window
        self.controls = [
            # Toolbar
            ft.Container(
                content=ft.Row([
                    ft.Text(
                        "CANopen Analyzer", 
                        size=20, 
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Container(expand=True),  # Spacer
                    ft.IconButton(
                        icon=ft.Icons.INFO,
                        tooltip="About",
                        on_click=self.show_about
                    )
                ]),
                bgcolor=ft.Colors.BLUE_50,
                padding=10
            ),
            
            # Main content area
            tabs,
            
            # Status bar
            status_bar
        ]
        
        self.expand = True
    
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
