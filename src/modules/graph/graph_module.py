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
        # self._setup_variable_drop_monitoring()
        
        # UI components
        self.control_panel = None
        self.debug_panel = None
        
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
            ft.Container(width=20),
            ft.Text("Monitor Node ID:", size=12),
            ft.TextField(
                width=80,
                height=35,
                value="2",
                hint_text="2",
                on_change=self.on_node_id_changed,
                text_size=12
            ),
            ft.Container(expand=True),
            ft.Text(f"Variables loaded: 0", size=12),
            ft.Text(f"Graphs: 0", size=12)
        ])
        
        # Debug panel
        self.debug_panel = ft.Container(
            content=ft.Column([
                ft.Text("📊 Graph Module Debug Info", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("Status: Not monitoring", size=10, color=ft.Colors.GREY_600),
                ft.Text("Last PDO: None", size=10, color=ft.Colors.GREY_600),
                ft.Text("Variables updated: 0", size=10, color=ft.Colors.GREY_600),
                ft.Text("Node filter: 2", size=10, color=ft.Colors.GREY_600),
            ]),
            padding=8,
            bgcolor=ft.Colors.GREY_50,
            border_radius=4,
            border=ft.border.all(1, ft.Colors.GREY_300)
        )
        
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
                    ),
                    ft.Container(height=10),
                    self.debug_panel
                ]),
                width=280,
                padding=ft.padding.only(right=10),
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5
            ),
            
            # Right panel - Graph display (75%)
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
                
                # Build COB-ID mapping in data collector
                self.data_collector.build_cob_id_mapping(od_module.pdo_mappings)
                
                # Build variables list in variable manager
                self.variable_manager.build_variables_list(
                    self.data_collector.cob_id_to_pdo, 
                    self.data_collector
                )
                
                # Set PDO variables in data collector for tracking
                self.data_collector.set_pdo_variables(self.variable_manager.pdo_variables)
                
                self.logger.info(f"Built variables list with {self.variable_manager.get_variable_count()} variables")
            else:
                self.logger.warning("No PDO mappings found in OD module")
                self.variable_manager.build_variables_list({}, self.data_collector)
            
            self.update_control_panel_stats()
            
            # Force UI update
            if self.page:
                self.page.update()
            
        except Exception as e:
            self.logger.error(f"Error loading OD data in Graph Module: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def on_node_id_changed(self, e):
        """Handle node ID selection change"""
        try:
            node_id_text = e.control.value.strip()
            if node_id_text == "":
                node_id = 2  # Default
            else:
                node_id = int(node_id_text)
            
            # Update data collector with selected node ID
            self.data_collector.set_monitored_node_id(node_id)
            
            # Update debug display
            self.update_debug_display("node_filter", f"Node filter: {node_id}")
            
            self.logger.info(f"Graph module - Node ID filter set to: {node_id}")
            
        except ValueError:
            self.logger.warning(f"Invalid node ID in graphs: {e.control.value}")
            e.control.value = "2"  # Reset to default
            self.page.update()
    
    def update_debug_display(self, field: str, value: str):
        """Update debug display information"""
        try:
            debug_controls = self.debug_panel.content.controls
            
            if field == "status":
                debug_controls[1].value = f"Status: {value}"
                debug_controls[1].color = ft.Colors.GREEN_600 if "monitoring" in value.lower() else ft.Colors.GREY_600
            elif field == "last_pdo":
                debug_controls[2].value = f"Last PDO: {value}"
                debug_controls[2].color = ft.Colors.BLUE_600
            elif field == "variables_updated":
                debug_controls[3].value = f"Variables updated: {value}"
                debug_controls[3].color = ft.Colors.ORANGE_600
            elif field == "node_filter":
                debug_controls[4].value = value
                debug_controls[4].color = ft.Colors.PURPLE_600
            
            if self.page:
                self.page.update()
                
        except Exception as e:
            self.logger.error(f"Error updating debug display: {e}")
    
    def start_data_collection(self, e):
        """Start collecting data from PDO messages"""
        try:
            if self.data_collector.start_collection():
                self.logger.info("🔍 DEBUG: GraphModule - Data collection started successfully")
                
                # Add debug callback FIRST
                self.data_collector.add_debug_callback(self.on_debug_message)
                
                # Then add data update callback
                self.data_collector.add_update_callback(self.on_data_updated)
                
                # UPDATE BUTTON STATES - ESTA LÍNEA FALTABA
                self.update_button_states()
                
                # Update debug display
                self.update_debug_display("status", "Data collection started")
                
                # Log current state
                # self.logger.info(f"🔍 DEBUG: GraphModule - Data collector monitoring node {self.data_collector.monitored_node_id}")
                # self.logger.info(f"🔍 DEBUG: GraphModule - Data collector has {len(self.data_collector.cob_id_to_pdo)} PDO mappings")
                # self.logger.info(f"🔍 DEBUG: GraphModule - Data collector tracking {len(self.data_collector.pdo_variables)} variables")
                
                # Test: Send a manual update to verify the chain works
                # self.logger.info("🔍 DEBUG: GraphModule - Testing update chain...")
                self.on_data_updated()
            else:
                self.logger.error("Failed to start data collection")
                self.update_debug_display("status", "Failed to start")
                
        except Exception as ex:
            self.logger.error(f"Error starting data collection: {ex}")
            self.update_debug_display("status", f"Error: {ex}")
    
    def stop_data_collection(self, e):
        """Stop collecting data"""
        try:
            self.data_collector.stop_collection()
            self.data_collector.remove_update_callback(self.on_data_updated)
            self.data_collector.remove_debug_callback(self.on_debug_message)
            self.update_button_states()
            self.update_debug_display("status", "Stopped")
            self.logger.info("Data collection stopped")
            
        except Exception as ex:
            self.logger.error(f"Error stopping data collection: {ex}")
    
    def on_debug_message(self, debug_info: dict):
        """Handle debug messages from data collector"""
        try:
            if debug_info.get("type") == "pdo_processed":
                pdo_info = f"0x{debug_info.get('cob_id', 0):03X} (Node {debug_info.get('node_id', 0)})"
                self.update_debug_display("last_pdo", pdo_info)
                
                var_count = debug_info.get("variables_updated", 0)
                self.update_debug_display("variables_updated", str(var_count))
                
        except Exception as e:
            self.logger.error(f"Error handling debug message: {e}")
    
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
    
    def update_control_panel_stats(self):
        """Update statistics in control panel"""
        try:
            var_count = self.variable_manager.get_variable_count()
            graph_count = len(self.graph_display.graphs)

            if self.control_panel and len(self.control_panel.controls) >= 8:
                # Update the last two Text controls (variables and graphs count)
                self.control_panel.controls[-2].value = f"Variables loaded: {var_count}"
                self.control_panel.controls[-1].value = f"Graphs: {graph_count}"

                # Force update of the control panel
                if hasattr(self.control_panel, 'update'):
                    self.control_panel.update()

            # Force update of the entire page
            if self.page and hasattr(self.page, 'update'):
                try:
                    self.page.update()
                except Exception as page_error:
                    self.logger.debug(f"Page update failed in stats update: {page_error}")
                    
            # Also force update of the graph display area
            if hasattr(self, 'graph_display') and self.graph_display:
                if hasattr(self.graph_display, 'graph_area') and self.graph_display.graph_area:
                    self.graph_display.graph_area.update()
            
            self.logger.debug(f"Stats updated: {var_count} variables, {graph_count} graphs")

        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def update_connection_status(self, connected: bool):
        """Manejador de cambios en el estado de conexión del interfaz"""
        try:
            self.logger.info(f"GraphModule - Conexión {'activa' if connected else 'desconectada'}")
            
            # Actualiza botones del panel de control si están disponibles
            self.update_button_states()
            
            # Actualiza el estado en el panel de depuración
            status_text = "Connected" if connected else "Disconnected"
            self.update_debug_display("status", status_text)

        except Exception as e:
            self.logger.error(f"Error en update_connection_status: {e}")
    
    def clear_data(self, e=None):
        """Limpia los datos de los gráficos"""
        try:
            self.data_collector.clear_data()
            self.graph_display.force_update()
            self.logger.info("Datos del módulo de gráficas limpiados correctamente")
            self.update_debug_display("status", "Datos limpiados")
        except Exception as ex:
            self.logger.error(f"Error al limpiar los datos del gráfico: {ex}")
    
    def setup_periodic_update(self):
        """Configura una actualización periódica de las gráficas"""
        try:
            if self.page:
                def periodic():
                    if self.interface_manager and self.interface_manager.is_connected():
                        self.graph_display.on_data_updated()

                    # Reprogramar
                    self.page.run_task_later(periodic, delay=1.0)  # Ejecuta cada segundo

                self.page.run_task_later(periodic, delay=1.0)
                self.logger.info("Actualización periódica de gráficas iniciada")

        except Exception as e:
            self.logger.error(f"Error configurando actualización periódica: {e}")

    # En graph_module.py, añade este método faltante:
    def update_button_states(self):
        """Update button enabled/disabled states"""
        try:
            if self.control_panel and len(self.control_panel.controls) >= 2:
                start_button = self.control_panel.controls[0]
                stop_button = self.control_panel.controls[1]
                
                is_connected = self.interface_manager.is_connected() if self.interface_manager else False
                is_collecting = self.data_collector.is_collecting  # CORRECCIÓN: usar is_collecting en lugar de is_monitoring
                
                start_button.disabled = not is_connected or is_collecting
                stop_button.disabled = not is_collecting
                
                if self.page:
                    self.page.update()
                    
        except Exception as e:
            self.logger.error(f"Error updating button states: {e}")

    def on_data_updated(self):
        """Handle data updates from data collector"""
        try:
            # self.logger.info(f"🔍 DEBUG: GraphModule - on_data_updated called")
            
            # Update the graph display
            if hasattr(self, 'graph_display') and self.graph_display:
                self.graph_display.update_display(
                    {},  # selected_variables (not used anymore)
                    self.data_collector.pdo_variables,
                    self.data_collector.variable_history,
                    self.data_collector.is_monitoring
                )
                
                # self.logger.info(f"🔍 DEBUG: GraphModule - Graph display updated with {len(self.data_collector.variable_history)} variable histories")
            
            # Update stats
            self.update_control_panel_stats()
            
        except Exception as e:
            self.logger.error(f"🔍 DEBUG: GraphModule - Error in on_data_updated: {e}")