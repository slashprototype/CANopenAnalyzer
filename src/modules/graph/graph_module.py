import flet as ft
from typing import Any, Dict, List

from interfaces import InterfaceManager
from .data_collector import DataCollector
from .variable_manager import VariableManager  
from .graph_display import GraphDisplay

class GraphModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: InterfaceManager = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        
        # Interface and OD reader references
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        self.od_reader_module = None
        self.variables_module = None
        
        # Initialize components
        self.data_collector = DataCollector(logger, self.interface_manager)
        self.variable_manager = VariableManager(logger, page)
        self.graph_display = GraphDisplay(logger, page)
        
        # Set up callbacks
        self.graph_display.set_stats_update_callback(self.update_control_panel_stats)
        
        # Add variable drop callback to force immediate updates
        self._setup_variable_drop_monitoring()
        
        # UI components
        self.control_panel = None
        
    def initialize(self):
        """Initialize the graph module"""
        self.logger.info("Initializing Graph Module")
        
        # Register for connection state changes
        if self.interface_manager:
            self.interface_manager.add_connection_callback(self.update_connection_status)
        
        self.build_interface()
        
        # Try to load OD data if already available
        self.auto_load_from_od_reader()
        
    def build_interface(self):
        """Build the graph module interface"""
        # Control panel
        self.control_panel = ft.Row([
            ft.ElevatedButton(
                "Start Data Collection",
                icon=ft.Icons.PLAY_ARROW,
                on_click=self.start_data_collection,
                disabled=not (self.interface_manager and self.interface_manager.is_connected()),
                height=35
            ),
            ft.ElevatedButton(
                "Stop Data Collection", 
                icon=ft.Icons.STOP,
                on_click=self.stop_data_collection,
                disabled=True,
                height=35
            ),
            ft.ElevatedButton(
                "Clear Data",
                icon=ft.Icons.CLEAR,
                on_click=self.clear_data,
                height=35
            ),
            ft.Container(expand=True),
            ft.Text(f"Variables loaded: 0", size=12),
            ft.Text(f"Graphs: 0", size=12)
        ])
        
        # Initialize UI components
        variables_list = self.variable_manager.initialize_ui()
        graph_area = self.graph_display.initialize_ui()
        
        # Start a periodic update for graph display
        self.setup_periodic_update()
        
        # Main layout - two columns with drag-drop target
        main_content = ft.Row([
            # Left panel - Variables selection (25%)
            ft.Container(
                content=ft.Column([
                    variables_list,
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text("💡 Drag variables to graphs", size=10, color=ft.Colors.BLUE_600),
                        padding=5,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=4,
                        border=ft.border.all(1, ft.Colors.BLUE_200)
                    )
                ]),
                width=280,
                padding=ft.padding.only(right=10),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5
            ),
            
            # Right panel - Graph display (75%) - Remove the outer DragTarget
            ft.Container(
                content=graph_area,
                expand=True,
                padding=ft.padding.only(left=10),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5
            )
        ], expand=True)
        
        # Build complete interface
        self.controls = [
            ft.Container(content=self.control_panel, padding=8),
            main_content
        ]
        self.expand = True
    
    def on_variable_dropped_to_graphs(self, e):
        """Handle variable dropped to graphs area (will be handled by individual graphs)"""
        # This method is no longer needed since individual graphs handle their own drops
        self.logger.debug("Variable dropped in general graph area")
    
    def set_od_reader_module(self, od_reader_module):
        """Set reference to OD reader module"""
        self.od_reader_module = od_reader_module
        self.logger.info("OD Reader module reference set in Graph Module")
        
        # Try to load OD data immediately if available
        if od_reader_module and hasattr(od_reader_module, "registers") and od_reader_module.registers:
            self.logger.info(f"Found {len(od_reader_module.registers)} registers in OD reader")
            self.load_od_data(od_reader_module)
        else:
            self.logger.info("No registers found in OD reader module yet")
    
    def set_variables_module(self, variables_module):
        """Set reference to variables module"""
        self.variables_module = variables_module
        self.logger.info("Variables module reference set in Graph Module")
    
    def auto_load_from_od_reader(self):
        """Automatically load OD data from OD reader if available"""
        try:
            if self.od_reader_module and hasattr(self.od_reader_module, "registers") and self.od_reader_module.registers:
                self.logger.info(f"Auto-loading OD data with {len(self.od_reader_module.registers)} registers")
                self.load_od_data(self.od_reader_module)
                self.logger.info("Auto-loaded OD data in Graph Module")
            else:
                self.logger.debug("No OD data available for auto-loading in Graph Module")
        except Exception as e:
            self.logger.debug(f"Could not auto-load from OD reader in Graph Module: {e}")
    
    def load_od_data(self, od_module):
        """Load OD data from OD reader module"""
        try:
            # Load OD data into variable manager
            self.variable_manager.load_od_data(od_module)
            self.logger.info(f"Loaded OD data into variable manager")
            
            # Load PDO mappings if available
            if hasattr(od_module, 'pdo_mappings') and od_module.pdo_mappings:
                self.logger.info(f"Found PDO mappings: {len(od_module.pdo_mappings)}")
                self.data_collector.build_cob_id_mapping(od_module.pdo_mappings)
                self.variable_manager.build_variables_list(
                    self.data_collector.cob_id_to_pdo, 
                    self.data_collector
                )
                self.logger.info(f"Built variables list with {self.variable_manager.get_variable_count()} variables")
            else:
                self.logger.warning("No PDO mappings found in OD module")
                # Still try to build an empty list to show the headers
                self.variable_manager.build_variables_list({}, self.data_collector)
            
            self.update_control_panel_stats()
            
            # Force UI update
            if self.page:
                self.page.update()
            
        except Exception as e:
            self.logger.error(f"Error loading OD data in Graph Module: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def start_data_collection(self, e):
        """Start collecting data from PDO messages"""
        if self.data_collector.start_collection():
            self.update_button_states()
    
    def stop_data_collection(self, e):
        """Stop collecting data"""
        self.data_collector.stop_collection()
        self.update_button_states()
    
    def clear_data(self, e):
        """Clear all collected data"""
        self.data_collector.clear_data()
        self.update_graph_display()
    
    def update_graph_display(self):
        """Update the graph display with current data"""
        self.graph_display.update_display(
            self.variable_manager.selected_variables,
            self.variable_manager.pdo_variables,
            self.data_collector.variable_history,
            self.data_collector.is_monitoring
        )
    
    def update_connection_status(self, connected: bool):
        """Update connection status (callback from interface manager)"""
        self.logger.info(f"Graph Module - connection status changed: {connected}")
        if not connected and self.data_collector.is_monitoring:
            self.stop_data_collection(None)
        
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled/disabled states"""
        if self.control_panel and len(self.control_panel.controls) >= 2:
            start_button = self.control_panel.controls[0]
            stop_button = self.control_panel.controls[1]
            
            is_connected = self.interface_manager.is_connected() if self.interface_manager else False
            start_button.disabled = not is_connected or self.data_collector.is_monitoring
            stop_button.disabled = not self.data_collector.is_monitoring
            
            if self.page:
                self.page.update()
    
    def update_control_panel_stats(self):
        """Update statistics in control panel"""
        if self.control_panel and len(self.control_panel.controls) >= 6:
            # Update variable count
            self.control_panel.controls[4].value = f"Variables loaded: {self.variable_manager.get_variable_count()}"
            # Update graphs count  
            self.control_panel.controls[5].value = f"Graphs: {len(self.graph_display.graphs)}"
            
            if self.page:
                self.page.update()
    
    def setup_periodic_update(self):
        """Setup periodic updates for graph display"""
        def update_graphs():
            if self.data_collector.is_monitoring:
                self.update_graph_display()
        
        # Update every 1 second when monitoring
        self.page.run_task(self.periodic_update_task)
    
    async def periodic_update_task(self):
        """Periodic task to update graphs"""
        import asyncio
        while True:
            if self.data_collector.is_monitoring:
                self.update_graph_display()
            await asyncio.sleep(1)
    
    def _setup_variable_drop_monitoring(self):
        """Setup monitoring for variable drops to force immediate UI updates"""
        # This will be called by individual graphs when variables are dropped
        pass
    
    def on_variable_assigned_to_graph(self):
        """Callback when a variable is assigned to any graph"""
        self.update_control_panel_stats()
        self.graph_display.force_update()
    
    # Backward compatibility methods
    def get_variable_data(self, var_index: str) -> List[tuple]:
        """Get historical data for a specific variable"""
        return self.data_collector.get_variable_data(var_index)
    
    def get_selected_variables_data(self) -> Dict[str, List[tuple]]:
        return self.variable_manager.get_selected_variables_data(self.data_collector)
