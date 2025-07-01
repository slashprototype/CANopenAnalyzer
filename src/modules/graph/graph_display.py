import flet as ft
import time
from typing import Set, Dict
from .individual_graph import IndividualGraph

class GraphDisplay:
    def __init__(self, logger, page):
        self.logger = logger
        self.page = page
        self.graph_area = None
        self._last_graph_update = 0
        
        # Graph management
        self.graphs = {}  # {graph_id: IndividualGraph}
        self.next_graph_id = 1
        
    def initialize_ui(self):
        """Initialize the graph display UI"""
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
        ], scroll=ft.ScrollMode.AUTO)
        
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
        
        return self.graph_area
    
    def add_new_graph(self, e=None):
        """Add a new individual graph"""
        graph_id = str(self.next_graph_id)
        self.next_graph_id += 1
        
        new_graph = IndividualGraph(
            graph_id=graph_id,
            logger=self.logger,
            on_remove_callback=self.remove_graph
        )
        
        self.graphs[graph_id] = new_graph
        
        # Add to UI
        self.update_graphs_display()
        
        self.logger.info(f"Added new graph: {graph_id}")
        
        if self.page:
            self.page.update()
    
    def remove_graph(self, graph_id: str):
        """Remove a graph"""
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            self.update_graphs_display()
            self.logger.info(f"Removed graph: {graph_id}")
            
            if self.page:
                self.page.update()
    
    def update_graphs_display(self):
        """Update the graphs display container"""
        if not self.graphs:
            self.graphs_container.controls = [
                ft.Text(
                    "Click 'Add Graph' to create a new graph.\n"
                    "Then drag variables from the left panel to each graph.",
                    text_align=ft.TextAlign.CENTER,
                    size=12,
                    color=ft.Colors.GREY_600
                )
            ]
        else:
            # Create a responsive grid layout
            self.graphs_container.controls = []
            
            # Add graphs in rows (2 per row)
            graph_list = list(self.graphs.values())
            for i in range(0, len(graph_list), 2):
                row_graphs = graph_list[i:i+2]
                if len(row_graphs) == 1:
                    # Single graph in row
                    self.graphs_container.controls.append(
                        ft.Row([row_graphs[0], ft.Container(expand=True)])
                    )
                else:
                    # Two graphs in row
                    self.graphs_container.controls.append(
                        ft.Row(row_graphs)
                    )
    
    def update_display(self, selected_variables: Set, pdo_variables: dict, variable_history: dict, is_monitoring: bool):
        """Update all graphs with current data"""
        # Throttle updates
        if time.time() - self._last_graph_update < 0.5:
            return
        
        # Update each individual graph
        for graph in self.graphs.values():
            graph.update_graph_content(pdo_variables, variable_history)
        
        # Update stats in parent module
        self.update_stats_callback()
        
        self._last_graph_update = time.time()
        
        if self.page:
            self.page.update()
    
    def set_stats_update_callback(self, callback):
        """Set callback for updating stats in parent module"""
        self.update_stats_callback = callback
    
    def force_update(self):
        """Force an immediate update of all graphs"""
        for graph in self.graphs.values():
            graph.update()
        
        if hasattr(self, 'update_stats_callback'):
            self.update_stats_callback()
        
        if self.page:
            self.page.update()

    def get_all_assigned_variables(self) -> Set[str]:
        """Get all variables assigned to any graph"""
        all_vars = set()
        for graph in self.graphs.values():
            all_vars.update(graph.assigned_variables)
        return all_vars
