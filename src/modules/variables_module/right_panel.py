import flet as ft
from .tracked_variable import TrackedVariable

class RightPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.variables_module = parent_module  # Keep separate reference to avoid Flet overwriting
        self.tracked_variables = []
        
        # Controls
        self.variables_table = None
        self.clear_button = None
        self.export_button = None
        self.write_dialog = None
        self.current_variable_for_write = None
    
    def initialize(self):
        """Initialize the right panel"""
        self.variables_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Index", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Category", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Type", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Current Value", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Last Update", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Updates", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", size=10, weight=ft.FontWeight.BOLD))
            ],
            rows=[],
            heading_row_height=30,
            data_row_min_height=25,
            data_row_max_height=30
        )
        
        self.clear_button = ft.ElevatedButton(
            "Clear All",
            icon=ft.Icons.CLEAR_ALL,
            on_click=self.clear_all_variables
        )
        
        self.export_button = ft.ElevatedButton(
            "Export Data",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.export_variables
        )
        
        self.controls = [
            ft.Row([
                ft.Text("Tracked Variables", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                self.clear_button,
                self.export_button
            ]),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    self.variables_table
                ], scroll=ft.ScrollMode.AUTO),
                expand=True,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10
            )
        ]
        self.expand = True
        
        # Initialize write dialog
        self._create_write_dialog()
    
    def _create_write_dialog(self):
        """Create the SDO write dialog"""
        self.value_input = ft.TextField(
            label="Value to write",
            helper_text="Enter value (decimal or hex with 0x prefix)",
            width=300
        )
        
        self.node_id_input = ft.TextField(
            label="Node ID",
            value="1",
            helper_text="Target node ID (1-127)",
            width=150
        )
        
        self.write_dialog = ft.AlertDialog(
            title=ft.Text("Write SDO Value"),
            content=ft.Column([
                ft.Text("Variable: ", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("", ref=ft.Ref[ft.Text]()),  # Will be updated with variable info
                ft.Divider(),
                self.node_id_input,
                self.value_input,
                ft.Text("Note: This will perform an expedited SDO transfer", 
                       size=12, italic=True, color=ft.Colors.BLUE_GREY)
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_write_dialog),
                ft.ElevatedButton("Write", on_click=self._perform_sdo_write, 
                                bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE)
            ],
            modal=True
        )
    
    def _show_write_dialog(self, variable: TrackedVariable):
        """Show the write dialog for a specific variable"""
        self.current_variable_for_write = variable
        
        # Update dialog content with variable info
        var_info = f"{variable.name} ({variable.index}:{variable.sub_index}) - {variable.data_type}"
        self.write_dialog.content.controls[1].value = var_info
        
        # Clear previous values
        self.value_input.value = ""
        self.node_id_input.value = "1"
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(self.write_dialog)
    
    def _close_write_dialog(self, e):
        """Close the write dialog"""
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.write_dialog.open = False
            self.variables_module.page.update()
    
    def _perform_sdo_write(self, e):
        """Perform the SDO write operation"""
        try:
            # Validate inputs
            if not self.current_variable_for_write:
                self._show_error("No variable selected")
                return
            
            value_str = self.value_input.value.strip()
            node_id_str = self.node_id_input.value.strip()
            
            if not value_str or not node_id_str:
                self._show_error("Please enter both value and node ID")
                return
            
            # Parse value
            try:
                if value_str.startswith('0x') or value_str.startswith('0X'):
                    value = int(value_str, 16)
                else:
                    value = int(value_str)
            except ValueError:
                self._show_error("Invalid value format")
                return
            
            # Parse node ID
            try:
                node_id = int(node_id_str)
                if node_id < 1 or node_id > 127:
                    self._show_error("Node ID must be between 1 and 127")
                    return
            except ValueError:
                self._show_error("Invalid node ID")
                return
            
            # Determine data size based on variable type
            data_size = self._get_data_size_for_type(self.current_variable_for_write.data_type)
            
            # Prepare SDO data
            sdo_data = {
                'index': self.current_variable_for_write.index,
                'subindex': self.current_variable_for_write.sub_index,
                'value': value,
                'size': data_size,
                'is_read': False,
                'node_id': node_id
            }
            
            # Send through interface manager
            if self.variables_module.interface_manager:
                success = self.variables_module.interface_manager.send_data(sdo_data)
                if success:
                    self._show_success(f"SDO write sent successfully to node {node_id}")
                    self._close_write_dialog(None)
                else:
                    self._show_error("Failed to send SDO write")
            else:
                self._show_error("No interface available")
                
        except Exception as ex:
            self._show_error(f"Error performing SDO write: {ex}")
    
    def _get_data_size_for_type(self, data_type: str) -> int:
        """Get data size in bits based on data type"""
        type_sizes = {
            'BOOLEAN': 8,
            'UNSIGNED8': 8,
            'INTEGER8': 8,
            'SIGNED8': 8,
            'UNSIGNED16': 16,
            'INTEGER16': 16,
            'SIGNED16': 16,
            'UNSIGNED32': 32,
            'INTEGER32': 32,
            'SIGNED32': 32,
            'REAL32': 32
        }
        return type_sizes.get(data_type.upper(), 32)  # Default to 32 bits
    
    def _show_error(self, message: str):
        """Show error message"""
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(
                ft.SnackBar(
                    content=ft.Text(message),
                    bgcolor=ft.Colors.RED_400
                )
            )
    
    def _show_success(self, message: str):
        """Show success message"""
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(
                ft.SnackBar(
                    content=ft.Text(message),
                    bgcolor=ft.Colors.GREEN_400
                )
            )
    
    def add_variable(self, variable: TrackedVariable):
        """Add variable to tracking table"""
        # Check if already tracking this variable
        for tracked in self.tracked_variables:
            if tracked.index == variable.index and tracked.sub_index == variable.sub_index:
                if hasattr(self.variables_module, 'page') and self.variables_module.page:
                    self.variables_module.page.open(
                        ft.SnackBar(
                            content=ft.Text(f"Variable {variable.index}:{variable.sub_index} already being tracked"),
                            bgcolor=ft.Colors.ORANGE_400
                        )
                    )
                return
        
        # Create new tracked variable
        new_tracked = TrackedVariable(
            index=variable.index,
            sub_index=variable.sub_index,
            name=variable.name,
            category=variable.category,
            data_type=variable.data_type
        )
        
        self.tracked_variables.append(new_tracked)
        self.update_table()
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(
                ft.SnackBar(
                    content=ft.Text(f"Added variable: {variable.name}"),
                    bgcolor=ft.Colors.GREEN_400
                )
            )
    
    def remove_variable(self, variable: TrackedVariable):
        """Remove variable from tracking"""
        if variable in self.tracked_variables:
            self.tracked_variables.remove(variable)
            self.update_table()
    
    def clear_all_variables(self, e):
        """Clear all tracked variables"""
        self.tracked_variables.clear()
        self.update_table()
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(
                ft.SnackBar(
                    content=ft.Text("All variables cleared"),
                    bgcolor=ft.Colors.BLUE_400
                )
            )
    
    def export_variables(self, e):
        """Export variables data"""
        # Placeholder for export functionality
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.open(
                ft.SnackBar(
                    content=ft.Text("Export functionality coming soon"),
                    bgcolor=ft.Colors.ORANGE_400
                )
            )
    
    def update_table(self):
        """Update the variables table"""
        self.variables_table.rows.clear()
        
        for var in self.tracked_variables:
            remove_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                icon_size=16,
                on_click=lambda e, v=var: self.remove_variable(v)
            )
            
            write_button = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=ft.Colors.BLUE,
                icon_size=16,
                tooltip="Write SDO value",
                on_click=lambda e, v=var: self._show_write_dialog(v)
            )
            
            last_update_str = "Never"
            if var.last_update:
                last_update_str = var.last_update.strftime("%H:%M:%S")
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(f"{var.index}:{var.sub_index}", size=10)),
                    ft.DataCell(ft.Text(var.name[:20], size=10)),
                    ft.DataCell(ft.Text(var.category, size=10)),
                    ft.DataCell(ft.Text(var.data_type, size=10)),
                    ft.DataCell(ft.Text(str(var.current_value), size=10)),
                    ft.DataCell(ft.Text(last_update_str, size=10)),
                    ft.DataCell(ft.Text(str(var.update_count), size=10)),
                    ft.DataCell(ft.Row([write_button, remove_button], spacing=5))
                ]
            )
            self.variables_table.rows.append(row)
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()
