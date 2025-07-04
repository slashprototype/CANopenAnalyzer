import flet as ft
from typing import Set, Dict, List, Callable, Tuple
import time

class IndividualGraph(ft.Container):
    def __init__(self, graph_id: str, logger, on_remove_callback: Callable):
        super().__init__()
        self.graph_id = graph_id
        self.logger = logger
        self.on_remove_callback = on_remove_callback
        
        # Graph state
        self.assigned_variables = set()  # Set of variable indices
        self.variable_info = {}  # Cache of variable info for display
        self.max_data_points = 50  # Maximum points to show on graph
        
        # UI components
        self.variables_display = None
        self.graph_content = None
        self.line_chart = None
        
        self.build_ui()
    
    def build_ui(self):
        """Build the individual graph UI"""
        # Compact header with title, variables, and remove button in one row
        self.header = ft.Row([
            ft.Text(f"Graph {self.graph_id}", size=12, weight=ft.FontWeight.BOLD),
            ft.Container(width=10),
            ft.Text("Variables:", size=10, color=ft.Colors.GREY_600),
            ft.Container(width=5),
            # Container for variable chips
            ft.Container(
                content=ft.Row([], spacing=5, wrap=True),
                expand=True
            ),
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                tooltip="Remove Graph",
                on_click=self.remove_graph,
                icon_size=14
            )
        ], spacing=5)
        
        # Create LineChart for real-time data - simplified configuration
        self.line_chart = ft.LineChart(
            data_series=[],
            border=ft.border.all(2, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
            horizontal_grid_lines=ft.ChartGridLines(
                interval=10, 
                color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), 
                width=1
            ),
            vertical_grid_lines=ft.ChartGridLines(
                interval=2, 
                color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), 
                width=1
            ),
            left_axis=ft.ChartAxis(
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels_size=32,
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLUE_GREY),
            min_y=0,
            max_y=100,
            interactive=True,
            expand=True
        )
        
        # Graph area with placeholder
        self.graph_content = ft.Container(
            content=ft.Column([
                ft.Text(
                    "📊 Drop variables here to start graphing",
                    text_align=ft.TextAlign.CENTER,
                    size=10,
                    color=ft.Colors.GREY_500
                ),
                self.line_chart
            ], spacing=5),
            height=280,  # Reduced height since header is more compact
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=4,
            padding=10
        )
        
        # Drag target area
        self.drag_target = ft.DragTarget(
            group="variables",
            content=ft.Column([
                self.header,
                ft.Divider(height=1),
                self.graph_content
            ], spacing=5),
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
            # Debug: Log the complete drop event
            self.logger.info(f"=== DROP EVENT DEBUG START ===")
            self.logger.info(f"Drop event received: type={type(e)}")
            
            # Extract variable index from the drag event
            var_index = None
            
            # Method 1: Try to get from src_id by finding the draggable control
            if hasattr(e, 'src_id') and e.src_id and hasattr(self, 'page') and self.page:
                try:
                    # Find the draggable control by its ID
                    draggable_control = self.page.get_control(e.src_id)
                    if draggable_control and hasattr(draggable_control, 'data'):
                        var_index = draggable_control.data
                        self.logger.info(f"Got variable index from draggable control via src_id: '{var_index}'")
                except Exception as ex:
                    self.logger.debug(f"Could not get control by src_id: {ex}")
            
            # Method 2: Try to get from the dragged control's data
            if not var_index and hasattr(e, 'control') and hasattr(e.control, 'content') and hasattr(e.control.content, 'data'):
                var_index = e.control.content.data
                self.logger.info(f"Got variable index from dragged control content data: '{var_index}'")
            
            # Method 3: Try to get from the draggable's data attribute
            if not var_index and hasattr(e, 'control') and hasattr(e.control, 'data'):
                var_index = e.control.data
                self.logger.info(f"Got variable index from dragged control data: '{var_index}'")
            
            # Method 4: Check if the event itself has data (Flet sometimes puts it here)
            if not var_index and hasattr(e, 'data') and e.data:
                # Skip JSON-formatted drag coordinates
                if not (isinstance(e.data, str) and e.data.startswith('{')):
                    var_index = e.data
                    self.logger.info(f"Got variable index from event data: '{var_index}'")
            
            # Method 5: Last resort - try to extract from any available source
            if not var_index:
                self.logger.info(f"Debug info - e.data: {getattr(e, 'data', 'None')}")
                self.logger.info(f"Debug info - e.src_id: {getattr(e, 'src_id', 'None')}")
                if hasattr(e, 'control'):
                    self.logger.info(f"Debug info - e.control: {e.control}")
                    self.logger.info(f"Debug info - e.control.__dict__: {getattr(e.control, '__dict__', 'None')}")
                    if hasattr(e.control, 'content'):
                        self.logger.info(f"Debug info - e.control.content: {e.control.content}")
                        self.logger.info(f"Debug info - e.control.content.__dict__: {getattr(e.control.content, '__dict__', 'None')}")
            
            if not var_index:
                self.logger.error(f"Could not extract variable index from drop event")
                self.logger.info(f"=== DROP EVENT DEBUG END ===")
                return
            
            # Ensure var_index is a string
            var_index = str(var_index)
            
            self.logger.info(f"Final extracted variable index: '{var_index}'")
            self.logger.info(f"=== DROP EVENT DEBUG END ===")
            
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
        """Update the variables display area with small chips"""
        try:
            # Get the variables container (4th element in header row)
            if len(self.header.controls) < 5:
                return
                
            variables_container = self.header.controls[4]
            variables_row = variables_container.content
            
            # Clear existing chips
            variables_row.controls.clear()
            
            if not self.assigned_variables:
                # Show placeholder when no variables
                variables_row.controls.append(
                    ft.Container(
                        content=ft.Text("None", size=12, color=ft.Colors.GREY_500),
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        bgcolor=ft.Colors.GREY_100,
                        border_radius=2,
                        border=ft.border.all(1, ft.Colors.GREY_300)
                    )
                )
            else:
                # Add small chips for each variable
                for var_index in sorted(self.assigned_variables):
                    # Get variable name
                    var_name = var_index
                    if var_index in self.variable_info:
                        var_name = self.variable_info[var_index]['name'][:8]  # Truncate to 8 chars
                    
                    # Create small chip
                    chip = ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    var_name,
                                    size=10,
                                    color=ft.Colors.WHITE,
                                    no_wrap=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=10,
                                    icon_color=ft.Colors.WHITE,
                                    style=ft.ButtonStyle(
                                        padding=0,
                                        shape=ft.RoundedRectangleBorder(radius=2),
                                    ),
                                    tooltip=f"Remove {var_index}",
                                    on_click=lambda e, vi=var_index: self.remove_variable(vi),
                                )
                            ],
                            spacing=4,
                            tight=True,
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        padding=ft.padding.symmetric(horizontal=6, vertical=4),
                        bgcolor=ft.Colors.BLUE_600,
                        border_radius=6,
                        border=ft.border.all(1, ft.Colors.BLUE_700),
                        height=28,
                    )
                    variables_row.controls.append(chip)
            
            # Safe update - only update if control is properly initialized
            try:
                self.update()
            except Exception as update_error:
                self.logger.debug(f"Update failed for graph {self.graph_id}: {update_error}")
            
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
                self._update_line_chart(variable_history)
                # Force UI update when new data arrives
                self.update()
                
                # Debug: Log data update
                data_points_count = sum(len(variable_history.get(var_index, [])) for var_index in self.assigned_variables)
                # self.logger.debug(f"🔍 DEBUG: Graph {self.graph_id} updated with {data_points_count} total data points")
            
        except Exception as e:
            self.logger.error(f"🔍 DEBUG: Error updating graph content for graph {self.graph_id}: {e}")
    
    
    def _update_line_chart(self, variable_history: dict):
        """Update the line chart with variable data"""
        try:
            data_series = []
            colors = [ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN, ft.Colors.ORANGE, ft.Colors.PURPLE]
            color_index = 0
            
            min_y = float('inf')
            max_y = float('-inf')
            has_data = False
            total_points = 0
            
            for var_index in sorted(self.assigned_variables):
                if var_index not in variable_history:
                    continue
                    
                history = variable_history[var_index]
                if not history:
                    continue
                
                # Get recent data points
                recent_data = history[-self.max_data_points:] if len(history) > self.max_data_points else history
                
                if not recent_data:
                    continue
                
                has_data = True
                total_points += len(recent_data)
                
                # Convert to chart data points
                data_points = []
                
                for i, (timestamp, value) in enumerate(recent_data):
                    try:
                        # Use index as x-axis for simplicity
                        x_val = i
                        y_val = float(value)
                        
                        data_points.append(ft.LineChartDataPoint(x_val, y_val))
                        
                        # Track min/max for axis scaling
                        min_y = min(min_y, y_val)
                        max_y = max(max_y, y_val)
                        
                    except (ValueError, TypeError) as e:
                        self.logger.debug(f"Error converting value {value} to float: {e}")
                        continue
                
                if data_points:
                    # Get variable name for legend
                    var_name = var_index
                    if var_index in self.variable_info:
                        var_name = f"{var_index}"
                    
                    series = ft.LineChartData(
                        data_points=data_points,
                        stroke_width=3,
                        color=colors[color_index % len(colors)],
                        curved=True,
                        stroke_cap_round=True,
                    )
                    data_series.append(series)
                    color_index += 1
            
            # Update chart
            if has_data:
                # Set reasonable axis limits with better scaling
                if min_y == max_y:
                    # If all values are the same, add some padding
                    self.line_chart.min_y = min_y - 1
                    self.line_chart.max_y = max_y + 1
                else:
                    # Add 10% padding on both ends
                    y_range = max_y - min_y
                    padding = y_range * 0.1
                    self.line_chart.min_y = min_y - padding
                    self.line_chart.max_y = max_y + padding
                
                # Update X-axis range to show recent data
                if len(recent_data) >= self.max_data_points:
                    self.line_chart.min_x = 0
                    self.line_chart.max_x = self.max_data_points
                else:
                    self.line_chart.min_x = 0
                    self.line_chart.max_x = max(10, len(recent_data))
                
                # Update chart title
                self.graph_content.content.controls[0] = ft.Text(
                    f"📈 {len(self.assigned_variables)} vars • {total_points} points",
                    text_align=ft.TextAlign.CENTER,
                    size=9,
                    color=ft.Colors.GREEN_600
                )
            else:
                # No data available
                self.graph_content.content.controls[0] = ft.Text(
                    f"⏳ Waiting for data... ({len(self.assigned_variables)} variables)",
                    text_align=ft.TextAlign.CENTER,
                    size=9,
                    color=ft.Colors.ORANGE_600
                )
            
            # Update data series
            self.line_chart.data_series = data_series
            
        except Exception as e:
            self.logger.error(f"Error updating line chart for graph {self.graph_id}: {e}")

    def remove_graph(self, e):
        """Remove this graph"""
        if self.on_remove_callback:
            self.on_remove_callback(self.graph_id)

    def remove_variable(self, var_index: str):
        """Remove a variable from this graph"""
        try:
            if var_index in self.assigned_variables:
                self.assigned_variables.remove(var_index)
                self.logger.info(f"Variable {var_index} removed from graph {self.graph_id}")
                self.update_variables_display()
        except Exception as e:
            self.logger.error(f"Error removing variable {var_index} from graph {self.graph_id}: {e}")
    
    def cleanup(self):
        """Clean up resources and references"""
        try:
            # Clear data structures
            self.assigned_variables.clear()
            self.variable_info.clear()
            
            # Clear UI references
            self.variables_display = None
            self.graph_content = None
            self.line_chart = None
            self.header = None
            self.drag_target = None
            
            # Clear callback reference
            self.on_remove_callback = None
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Error in IndividualGraph cleanup: {e}")

