import flet as ft
import time
import threading
from typing import Set, Dict
from .individual_graph import IndividualGraph

class GraphDisplay:
    def __init__(self, logger, page):
        self.logger = logger
        self.page = page
        self.graph_area = None
        self._last_graph_update = 0
        self.update_interval = 1.0  # INCREASED: Update every 1 second instead of 500ms
        
        # Graph management
        self.graphs = {}  # {graph_id: IndividualGraph}
        self.next_graph_id = 1
        
        # Data references
        self.data_collector = None
        
        # ADDED: Asynchronous update management
        self._update_pending = False
        self._update_lock = threading.Lock()
        self._last_data_update = 0
        
        # ADDED: Control lifecycle management
        self._control_cleanup_pending = []
        self._ui_initialized = False
    
    def initialize_ui(self):
        """Initialize the graph display UI"""
        try:
            # Header with controls
            self.header = ft.Row([
                ft.Text("Graph Visualization", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Add Graph",
                    icon=ft.Icons.ADD,
                    on_click=self.add_new_graph,
                    height=30
                )
            ])
            
            # Scrollable area for graphs
            self.graphs_container = ft.Column([
                ft.Text(
                    "Click 'Add Graph' to create a new graph.\n"
                    "Then drag variables from the left panel to each graph.",
                    text_align=ft.TextAlign.CENTER,
                    size=12,
                    color=ft.Colors.GREY_600
                )
            ], scroll=ft.ScrollMode.AUTO, expand=True)
            
            self.graph_area = ft.Container(
                content=ft.Column([
                    self.header,
                    ft.Divider(height=1),
                    ft.Container(
                        content=self.graphs_container,
                        expand=True,
                        padding=10
                    )
                ]),
                expand=True
            )
            
            self._ui_initialized = True
            return self.graph_area
            
        except Exception as e:
            self.logger.error(f"Error initializing graph display UI: {e}")
            return ft.Container(content=ft.Text("Error initializing graph display"))
    
    def add_new_graph(self, e=None):
        """Add a new individual graph with proper error handling"""
        try:
            if not self._ui_initialized:
                self.logger.warning("Cannot add graph - UI not initialized")
                return
                
            graph_id = str(self.next_graph_id)
            self.next_graph_id += 1
            
            # Create new graph with proper error handling
            new_graph = IndividualGraph(
                graph_id=graph_id,
                logger=self.logger,
                on_remove_callback=self.remove_graph
            )
            
            # Ensure the graph is properly initialized before adding
            if new_graph and hasattr(new_graph, 'content'):
                self.graphs[graph_id] = new_graph
                
                # Update UI safely
                self._safe_update_graphs_display()
                
                self.logger.info(f"Added new graph: {graph_id}")
            else:
                self.logger.error(f"Failed to create graph {graph_id} - invalid graph object")
                
        except Exception as ex:
            self.logger.error(f"Error adding new graph: {ex}")
    
    def remove_graph(self, graph_id: str):
        """Remove a graph with proper cleanup"""
        try:
            if graph_id in self.graphs:
                # Mark graph for cleanup
                graph_to_remove = self.graphs[graph_id]
                self._control_cleanup_pending.append(graph_to_remove)
                
                # Remove from active graphs
                del self.graphs[graph_id]
                
                # Update display safely
                self._safe_update_graphs_display()
                
                self.logger.info(f"Removed graph: {graph_id}")
                
        except Exception as ex:
            self.logger.error(f"Error removing graph: {ex}")
    
    def _safe_update_graphs_display(self):
        """Safely update the graphs display container"""
        try:
            if not self._ui_initialized or not hasattr(self, 'graphs_container'):
                return
                
            # Clean up pending controls first
            self._cleanup_pending_controls()
            
            if not self.graphs:
                # No graphs - show placeholder
                placeholder = ft.Text(
                    "Click 'Add Graph' to create a new graph.\n"
                    "Then drag variables from the left panel to each graph.",
                    text_align=ft.TextAlign.CENTER,
                    size=12,
                    color=ft.Colors.GREY_600
                )
                self.graphs_container.controls = [placeholder]
            else:
                # Create new layout with proper control management
                new_controls = []
                
                # Add graphs in rows (2 per row) with safe control creation
                graph_list = list(self.graphs.values())
                for i in range(0, len(graph_list), 2):
                    row_graphs = graph_list[i:i+2]
                    
                    # Create row with proper error handling
                    try:
                        if len(row_graphs) == 1:
                            # Single graph in row
                            row = ft.Row([
                                row_graphs[0], 
                                ft.Container(expand=True)
                            ])
                        else:
                            # Two graphs in row
                            row = ft.Row(row_graphs)
                        
                        new_controls.append(row)
                    except Exception as row_error:
                        self.logger.error(f"Error creating graph row: {row_error}")
                        continue
                
                # Update controls safely
                self.graphs_container.controls = new_controls
            
            # Safe update with error handling
            try:
                if hasattr(self.graphs_container, 'update'):
                    self.graphs_container.update()
            except Exception as update_error:
                self.logger.debug(f"Graphs container update failed: {update_error}")
                
        except Exception as e:
            self.logger.error(f"Error in _safe_update_graphs_display: {e}")
    
    def _cleanup_pending_controls(self):
        """Clean up controls marked for removal"""
        try:
            if self._control_cleanup_pending:
                # Clear references to old controls
                for control in self._control_cleanup_pending:
                    try:
                        # Clear any circular references
                        if hasattr(control, 'cleanup'):
                            control.cleanup()
                    except Exception as cleanup_error:
                        self.logger.debug(f"Control cleanup error: {cleanup_error}")
                
                self._control_cleanup_pending.clear()
        except Exception as e:
            self.logger.error(f"Error cleaning up pending controls: {e}")

    def update_graphs_display(self):
        """Legacy method - redirects to safe update"""
        self._safe_update_graphs_display()
    
    def set_data_collector(self, data_collector):
        """Set reference to data collector for real-time updates"""
        self.data_collector = data_collector
        if data_collector:
            data_collector.add_update_callback(self.on_data_updated)
            self.logger.info("Connected graph display to data collector")
    
    def on_data_updated(self):
        """Called when data collector receives new data - OPTIMIZED VERSION"""
        try:
            current_time = time.time()
            
            # IMPROVED: More aggressive throttling
            if current_time - self._last_graph_update < self.update_interval:
                return
            
            # ADDED: Prevent concurrent updates
            with self._update_lock:
                if self._update_pending:
                    return
                self._update_pending = True
            
            # ADDED: Schedule update in background thread to avoid blocking
            def background_update():
                try:
                    self._last_graph_update = current_time
                    
                    # Update all individual graphs with actual data
                    if self.data_collector and self.graphs:
                        for graph in self.graphs.values():
                            try:
                                graph.update_graph_content(
                                    self.data_collector.pdo_variables, 
                                    self.data_collector.variable_history
                                )
                            except Exception as graph_error:
                                self.logger.debug(f"Error updating individual graph: {graph_error}")
                    
                    # MODIFIED: Reduced frequency UI updates
                    # Only update UI every few data updates
                    if current_time - self._last_data_update > 2.0:  # Every 2 seconds
                        self._last_data_update = current_time
                        if self.page and self._ui_initialized:
                            try:
                                self.page.update()
                            except Exception as page_error:
                                self.logger.debug(f"Page update failed: {page_error}")
                            
                except Exception as e:
                    self.logger.error(f"Error in background graph update: {e}")
                finally:
                    with self._update_lock:
                        self._update_pending = False
            
            # ADDED: Run update in background thread
            threading.Thread(target=background_update, daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Error handling data update: {e}")
            with self._update_lock:
                self._update_pending = False

    def update_display(self, selected_variables, pdo_variables, variable_history, is_monitoring):
        """Update the display with current data"""
        try:
            if not self._ui_initialized:
                return
                
            # Update all individual graphs
            for graph in self.graphs.values():
                try:
                    graph.update_graph_content(pdo_variables, variable_history)
                except Exception as graph_error:
                    self.logger.debug(f"Error updating graph in update_display: {graph_error}")
            
            # Force UI update safely
            try:
                if hasattr(self, 'page') and self.page and self._ui_initialized:
                    self.page.update()
            except Exception as page_error:
                self.logger.debug(f"Page update failed in update_display: {page_error}")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error updating graph display: {e}")
    
    def force_update(self):
        """Force update of all graphs with error handling"""
        try:
            if hasattr(self, 'page') and self.page and self._ui_initialized:
                self.page.update()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Error forcing graph update: {e}")
    
    def set_stats_update_callback(self, callback):
        """Set callback for stats updates"""
        self.stats_update_callback = callback

    def get_all_assigned_variables(self) -> Set[str]:
        """Get all variables assigned to any graph"""
        all_vars = set()
        for graph in self.graphs.values():
            try:
                all_vars.update(graph.assigned_variables)
            except Exception as e:
                self.logger.debug(f"Error getting variables from graph: {e}")
        return all_vars
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self._ui_initialized = False
            self._cleanup_pending_controls()
            
            # Clear graph references
            for graph in self.graphs.values():
                try:
                    if hasattr(graph, 'cleanup'):
                        graph.cleanup()
                except Exception as cleanup_error:
                    self.logger.debug(f"Graph cleanup error: {cleanup_error}")
            
            self.graphs.clear()
        except Exception as e:
            self.logger.error(f"Error in GraphDisplay cleanup: {e}")

