import flet as ft
from .tracked_variable import TrackedVariable

class RightPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.variables_module = parent_module
        self.tracked_variables = []
        
        # Dialog management - simplified
        self.write_dialog = None
        self.current_variable_for_write = None

        # Controls
        self.variables_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Index", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Name", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Category", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Length (bytes)", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Current Value", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Last Update", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Updates", size=13, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", size=13, weight=ft.FontWeight.BOLD))
            ],
            rows=[],
            heading_row_height=30,
            data_row_min_height=25,
            data_row_max_height=30
        )

    def initialize(self):
        """Initialize the right panel"""
        # Write dialog controls
        self.node_id_input = ft.TextField(
            label="Node ID",
            value="1",
            width=100,
            text_size=14
        )
        
        self.value_input = ft.TextField(
            label="Value",
            hint_text="Decimal or hex (0x...)",
            width=200,
            text_size=14
        )
        
        # Create dialog but don't add it to page yet
        self.write_dialog = None
        self.current_variable_for_write = None

        # Node ID field for the panel
        self.panel_node_id = ft.TextField(
            label="Default Node ID",
            value="2",
            width=120,
            text_size=14,
            tooltip="Node ID used for read/write operations"
        )

        # Create action buttons for the panel
        action_buttons = ft.Row([
            self.panel_node_id,
            ft.ElevatedButton(
                "Clear All",
                icon=ft.Icons.CLEAR_ALL,
                on_click=self.clear_all_variables
            ),
            ft.ElevatedButton(
                "Export",
                icon=ft.Icons.DOWNLOAD,
                on_click=self.export_variables
            ),
        ], spacing=10)

        # Add controls to the panel
        self.controls = [
            ft.Text("Tracked Variables", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            action_buttons,
            self.variables_table,
        ]

        # Initialize with empty content
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()

    def add_variable(self, variable: TrackedVariable):
        """Add variable to tracking table"""
        # Check if already tracking this variable
        for tracked in self.tracked_variables:
            if tracked.index == variable.index:
                if hasattr(self.variables_module, 'page') and self.variables_module.page:
                    self.variables_module.page.open(
                        ft.SnackBar(
                            content=ft.Text(f"Variable {variable.index} already being tracked"),
                            bgcolor=ft.Colors.ORANGE_400
                        )
                    )
                return
        
        # Create new tracked variable using only od_c_parser data
        new_tracked = TrackedVariable(
            index=variable.index,
            name=variable.name,
            category=variable.category,
            data_length=variable.data_length
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

    def update_table(self):
        """Update the variables table"""
        self.variables_table.rows.clear()
        
        for var in self.tracked_variables:
            remove_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                icon_size=20,
                on_click=lambda e, v=var: self.remove_variable(v)
            )
            
            write_button = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=ft.Colors.BLUE,
                icon_size=20,
                tooltip="Write SDO value",
                on_click=lambda e, v=var: self._show_write_dialog(v)
            )
            
            read_button = ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=ft.Colors.GREEN,
                icon_size=20,
                tooltip="Read current value",
                on_click=lambda e, v=var: self._read_variable_value(v)
            )
            
            last_update_str = "Never"
            if var.last_update:
                last_update_str = var.last_update.strftime("%H:%M:%S")
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(var.index, size=13)),
                    ft.DataCell(ft.Text(var.name, size=13)),
                    ft.DataCell(ft.Text(var.category, size=13)),
                    ft.DataCell(ft.Text(str(var.data_length), size=13)),
                    ft.DataCell(ft.Text(str(var.current_value), size=13)),
                    ft.DataCell(ft.Text(last_update_str, size=13)),
                    ft.DataCell(ft.Text(str(var.update_count), size=13)),
                    ft.DataCell(ft.Row([read_button, write_button, remove_button], spacing=5))
                ]
            )
            self.variables_table.rows.append(row)
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()

    def _create_write_dialog(self, variable: TrackedVariable):
        """Create a new write dialog for the variable"""
        value_field = ft.TextField(
            label="Value",
            hint_text="Decimal or hex (0x...)",
            width=200,
            text_size=14
        )
        
        # Use the panel's node ID as default
        default_node_id = self.panel_node_id.value if hasattr(self, 'panel_node_id') and self.panel_node_id.value else "2"
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Write Variable: {variable.name} ({variable.index})"),
            content=ft.Column([
                ft.Text("Enter value to write:"),
                value_field,
                ft.Text(f"Using Node ID: {default_node_id}", size=12, color=ft.Colors.GREY_600),
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.variables_module.page.close(dialog)),
                ft.TextButton("Write", on_click=lambda e: self._perform_write_simplified(e, variable, value_field, dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        return dialog

    def _show_write_dialog(self, variable: TrackedVariable):
        """Show write dialog for variable"""
        try:
            if not self.variables_module.page:
                print("Error: Page not available")
                return
            
            # Store current variable
            self.current_variable_for_write = variable
            
            # Create dialog
            self.write_dialog = self._create_write_dialog(variable)
            
            # Open dialog using official method
            self.variables_module.page.open(self.write_dialog)
            
        except Exception as e:
            print(f"Error showing write dialog: {e}")
            import traceback
            traceback.print_exc()

    def _perform_write_with_fields(self, e, variable: TrackedVariable, value_field: ft.TextField, node_id_field: ft.TextField, dialog: ft.AlertDialog):
        """Perform variable write with direct field references"""
        try:
            if not variable:
                self._show_error("No variable selected")
                return

            value_str = value_field.value.strip() if value_field.value else ""
            node_id_str = node_id_field.value.strip() if node_id_field.value else ""

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

            # Close dialog first using official method
            self.variables_module.page.close(dialog)
            
            # Send write request
            success = self.variables_module.write_variable(variable, value, node_id)
            if success:
                print(f"SDO write request sent successfully")
            else:
                self._show_error("Failed to send SDO write request")

        except Exception as ex:
            print(f"Error performing write: {ex}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Error performing write: {ex}")

    def _perform_write_simplified(self, e, variable: TrackedVariable, value_field: ft.TextField, dialog: ft.AlertDialog):
        """Perform variable write using panel's node ID"""
        try:
            if not variable:
                self._show_error("No variable selected")
                return

            value_str = value_field.value.strip() if value_field.value else ""

            if not value_str:
                self._show_error("Please enter a value")
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

            # Get node ID from panel
            try:
                node_id_str = self.panel_node_id.value.strip() if hasattr(self, 'panel_node_id') and self.panel_node_id.value else "2"
                node_id = int(node_id_str)
                if node_id < 1 or node_id > 127:
                    self._show_error("Node ID must be between 1 and 127")
                    return
            except ValueError:
                self._show_error("Invalid node ID in panel")
                return

            # Close dialog first using official method
            self.variables_module.page.close(dialog)
            
            # Send write request
            success = self.variables_module.write_variable(variable, value, node_id)
            if success:
                print(f"SDO write request sent successfully")
            else:
                self._show_error("Failed to send SDO write request")

        except Exception as ex:
            print(f"Error performing write: {ex}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Error performing write: {ex}")

    def _show_error(self, message: str):
        """Show error message"""
        try:
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.open(
                    ft.SnackBar(
                        content=ft.Text(message), 
                        bgcolor=ft.Colors.RED_400
                    )
                )
        except Exception as e:
            print(f"Error in _show_error: {e}")

    def _show_success(self, message: str):
        """Show success message"""
        try:
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.open(
                    ft.SnackBar(
                        content=ft.Text(message), 
                        bgcolor=ft.Colors.GREEN_400
                    )
                )
        except Exception as e:
            print(f"Error in _show_success: {e}")

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

    def _read_variable_value(self, variable: TrackedVariable):
        """Read current value of the variable"""
        try:
            # Get node ID from panel
            try:
                node_id_str = self.panel_node_id.value.strip() if hasattr(self, 'panel_node_id') and self.panel_node_id.value else "2"
                node_id = int(node_id_str)
                if node_id < 1 or node_id > 127:
                    self._show_error("Invalid Node ID in panel")
                    return
            except ValueError:
                self._show_error("Invalid Node ID format in panel")
                return
            
            # Call the module's read method
            success = self.variables_module.read_variable(variable, node_id)
            
            if success:
                self._show_success(f"Reading {variable.name}...")
            else:
                self._show_error(f"Failed to send read request for {variable.name}")
                
        except Exception as e:
            self.logger.error(f"Error reading variable {variable.name}: {e}")
            self._show_error(f"Error reading variable: {e}")