import flet as ft
from typing import Set, Dict, List, Callable

class IndividualGraph(ft.Container):
    def __init__(self, graph_id: str, logger, on_remove_callback: Callable):
        super().__init__()
        self.graph_id = graph_id
        self.logger = logger
        self.on_remove_callback = on_remove_callback
        
        # Graph state
        self.assigned_variables = set()  # Set of variable indices
        self.variable_info = {}  # Cache of variable info for display
        
        # UI components
        self.variables_display = None
        self.graph_content = None
        
        self.build_ui()
    
    def build_ui(self):
        """Build the individual graph UI"""
        # Header with title and remove button
        self.header = ft.Row([
            ft.Text(f"Graph {self.graph_id}", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                tooltip="Remove Graph",
                on_click=self.remove_graph,
                icon_size=16
            )
        ])
        
        # Variables display area
        self.variables_display = ft.Column([
            ft.Container(
                content=ft.Text(
                    "Variables:",
                    size=12,
                    weight=ft.FontWeight.W_500
                ),
                padding=ft.padding.only(bottom=5)
            ),
            ft.Container(
                content=ft.Text(
                    "Assigned variables: 0\nWaiting for data...",
                    size=10,
                    color=ft.Colors.GREY_600
                ),
                padding=5,
                bgcolor=ft.Colors.GREY_50,
                border_radius=4,
                border=ft.border.all(1, ft.Colors.GREY_300)
            )
        ])
        
        # Graph area (placeholder for now)
        self.graph_content = ft.Container(
            content=ft.Text(
                "📊 Graph will appear here when data collection starts",
                text_align=ft.TextAlign.CENTER,
                size=11,
                color=ft.Colors.GREY_500
            ),
            height=200,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=4,
            alignment=ft.alignment.center
        )
        
        # Drag target area
        self.drag_target = ft.DragTarget(
            group="variables",
            content=ft.Column([
                self.header,
                ft.Divider(height=1),
                self.variables_display,
                ft.Container(height=10),
                self.graph_content
            ]),
            on_accept=self.on_variable_dropped
        )
        
        # Container setup
        self.content = self.drag_target
        self.padding = 10
        self.border = ft.border.all(1, ft.Colors.BLUE_200)
        self.border_radius = 6
        self.bgcolor = ft.Colors.BLUE_50
        self.width = 400
        self.expand = True
    
    def on_variable_dropped(self, e):
        """Handle variable dropped on this graph"""
        try:
            # Extract variable index from the drag event
            var_index = None
            
            # Try to get from data attribute first
            if hasattr(e, 'data') and e.data:
                var_index = e.data
                self.logger.debug(f"Got variable index from data: {var_index}")
            
            # Fallback to src_id if data is not available
            if not var_index and hasattr(e, 'src_id') and e.src_id:
                var_index = e.src_id
                self.logger.debug(f"Got variable index from src_id: {var_index}")
            
            if not var_index:
                self.logger.error(f"Could not extract variable index from drop event: {e}")
                return
            
            self.logger.info(f"Variable {var_index} dropped on graph {self.graph_id}")
            
            # Check if variable is already assigned
            if var_index in self.assigned_variables:
                self.logger.info(f"Variable {var_index} already assigned to graph {self.graph_id}")
                return
            
            # Add variable to assigned set
            self.assigned_variables.add(var_index)
            self.logger.info(f"Variable {var_index} successfully added to graph {self.graph_id}")
            
            # Update display immediately
            self.update_variables_display()
            
        except Exception as ex:
            self.logger.error(f"Error handling variable drop on graph {self.graph_id}: {ex}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def update_variables_display(self):
        """Update the variables display area"""
        try:
            if not self.assigned_variables:
                display_text = "Assigned variables: 0\nDrop variables here to add them to this graph"
                color = ft.Colors.GREY_600
                bgcolor = ft.Colors.GREY_50
                border_color = ft.Colors.GREY_300
            else:
                var_names = []
                for var_index in sorted(self.assigned_variables):
                    if var_index in self.variable_info:
                        var_info = self.variable_info[var_index]
                        var_names.append(f"• {var_index} - {var_info['name'][:20]}")
                    else:
                        var_names.append(f"• {var_index}")
                
                display_text = f"Assigned variables: {len(self.assigned_variables)}\n" + "\n".join(var_names)
                color = ft.Colors.GREEN_700
                bgcolor = ft.Colors.GREEN_50
                border_color = ft.Colors.GREEN_300
            
            # Update the display container
            if self.variables_display and len(self.variables_display.controls) > 1:
                self.variables_display.controls[1].content.value = display_text
                self.variables_display.controls[1].content.color = color
                self.variables_display.controls[1].bgcolor = bgcolor
                self.variables_display.controls[1].border = ft.border.all(1, border_color)
            
            # Force update
            self.update()
            
        except Exception as e:
            self.logger.error(f"Error updating variables display for graph {self.graph_id}: {e}")
    
    def update_graph_content(self, pdo_variables: dict, variable_history: dict):
        """Update graph content with current data"""
        try:
            # Cache variable info for display
            for var_index in self.assigned_variables:
                if var_index in pdo_variables:
                    self.variable_info[var_index] = pdo_variables[var_index]
            
            # Update variables display
            self.update_variables_display()
            
            # Update graph content based on available data
            if self.assigned_variables and variable_history:
                # Check if we have data for any assigned variables
                has_data = any(
                    var_index in variable_history and len(variable_history[var_index]) > 0
                    for var_index in self.assigned_variables
                )
                
                if has_data:
                    # Show data status
                    data_points = sum(
                        len(variable_history.get(var_index, []))
                        for var_index in self.assigned_variables
                    )
                    self.graph_content.content = ft.Text(
                        f"📈 Collecting data...\n{data_points} total data points",
                        text_align=ft.TextAlign.CENTER,
                        size=11,
                        color=ft.Colors.GREEN_600
                    )
                    self.graph_content.bgcolor = ft.Colors.GREEN_50
                    self.graph_content.border = ft.border.all(1, ft.Colors.GREEN_300)
                else:
                    self.graph_content.content = ft.Text(
                        f"⏳ Waiting for data...\nVariables assigned: {len(self.assigned_variables)}",
                        text_align=ft.TextAlign.CENTER,
                        size=11,
                        color=ft.Colors.ORANGE_600
                    )
                    self.graph_content.bgcolor = ft.Colors.ORANGE_50
                    self.graph_content.border = ft.border.all(1, ft.Colors.ORANGE_300)
            
        except Exception as e:
            self.logger.error(f"Error updating graph content for graph {self.graph_id}: {e}")
    
    def remove_graph(self, e):
        """Remove this graph"""
        self.on_remove_callback(self.graph_id)
        # else:
        #     self.graph_area.content.content = ft.Text(
        #         f"Assigned variables: {len(self.assigned_variables)}\nWaiting for data...",
        #         text_align=ft.TextAlign.CENTER,
        #         size=11
        #     )
    
    def on_resize(self, e):
        """Handle graph resize"""
        try:
            new_width = max(300, self.width + e.delta_x)
            new_height = max(200, self.height + e.delta_y)
            
            self.width = new_width
            self.height = new_height
            
            if hasattr(self, 'page') and self.page:
                self.page.update()
                
        except Exception as ex:
            self.logger.error(f"Error resizing graph: {ex}")
    
    def remove_graph(self, e):
        """Remove this graph"""
        if self.on_remove_callback:
            self.on_remove_callback(self.graph_id)
