import flet as ft
from .tracked_variable import TrackedVariable
from typing import Dict, Any

class LeftPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.variables_module = parent_module
        self.available_variables = []
        self.filtered_variables = []
        self.selected_variable = None

        # Controls
        self.category_filter = None
        self.search_field = None
        self.variables_list = None
        self.add_button = None
        self.status_text = None
        self.refresh_button = None

    def initialize(self):
        """Initialize the left panel"""
        self.category_filter = ft.Dropdown(
            label="Category Filter",
            options=[
                ft.dropdown.Option("All"),
                ft.dropdown.Option("Communication"),
                ft.dropdown.Option("Manufacturer"),
                ft.dropdown.Option("Device Profile"),
                ft.dropdown.Option("Reserved"),
                ft.dropdown.Option("Unknown")
            ],
            value="All",
            width=150,
            on_change=self.filter_variables,
            
        )
        
        self.search_field = ft.TextField(
            width=220,
            label="Search variables",
            hint_text="Enter variable name or index",
            on_change=self.filter_variables,
            
        )
        
        self.variables_list = ft.ListView(height=300, spacing=2)
        
        self.add_button = ft.ElevatedButton(
            "Add Variable",
            icon=ft.Icons.ADD,
            on_click=self.add_selected_variable,
            disabled=True
        )
        
        self.refresh_button = ft.ElevatedButton(
            "Refresh from OD Reader",
            icon=ft.Icons.REFRESH,
            on_click=self.refresh_from_od_reader,
            tooltip="Load variables from OD Reader module"
        )
        
        self.status_text = ft.Text(
            "Load OD.c file to see variables",
            size=12,
            color=ft.Colors.GREY_600
        )
        
        self.controls = [
            ft.Text("Variable Selection", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            self.refresh_button,
            ft.Divider(height=1),
            ft.Row([self.category_filter, self.search_field], spacing=10),
            ft.Container(
                content=self.variables_list,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=5
            ),
            self.add_button,
            self.status_text
        ]
        self.expand = True

    def refresh_from_od_reader(self, e):
        """Refresh variables from OD Reader module"""
        try:
            od_module = self.variables_module.get_od_reader_module()
            
            if od_module and hasattr(od_module, "registers") and od_module.registers:
                self.load_variables_from_od(od_module)
                self.status_text.value = "Refreshed from OD Reader module"
                self.status_text.color = ft.Colors.GREEN
                
                if hasattr(self.variables_module, 'page') and self.variables_module.page:
                    self.variables_module.page.open(
                        ft.SnackBar(
                            content=ft.Text("Variables refreshed from OD Reader"),
                            bgcolor=ft.Colors.GREEN_400
                        )
                    )
            else:
                self.status_text.value = "No OD data found in OD Reader module"
                self.status_text.color = ft.Colors.ORANGE
                
                if hasattr(self.variables_module, 'page') and self.variables_module.page:
                    self.variables_module.page.open(
                        ft.SnackBar(
                            content=ft.Text("No OD data available. Load an OD.c file in OD Reader module first."),
                            bgcolor=ft.Colors.ORANGE_400
                        )
                    )
                
        except Exception as e:
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.Colors.RED
            
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.open(
                    ft.SnackBar(
                        content=ft.Text(f"Error refreshing from OD reader: {str(e)}"),
                        bgcolor=ft.Colors.RED_400
                    )
                )
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()

    def load_variables_from_od(self, od_module_or_registers):
        """Load variables from OD.c registers - accepts either od_module or registers list"""
        self.available_variables.clear()
        
        # Handle both od_module object and direct registers list
        if hasattr(od_module_or_registers, 'registers'):
            # It's an od_module object
            registers = od_module_or_registers.registers
        elif isinstance(od_module_or_registers, list):
            # It's a direct registers list
            registers = od_module_or_registers
        else:
            self.status_text.value = "Invalid data format"
            self.status_text.color = ft.Colors.RED
            return
        
        if not registers:
            self.status_text.value = "No OD.c data available"
            self.status_text.color = ft.Colors.RED
            return
        
        for reg in registers:
            # Handle both 'dataLength' and 'data_length' keys
            data_length = reg.get('data_length', reg.get('dataLength', 1))
            
            var = TrackedVariable(
                index=reg['index'],
                name=reg['name'],
                category=reg['category'],
                data_length=data_length
            )
            self.available_variables.append(var)
        
        self.status_text.value = f"Loaded {len(self.available_variables)} variables"
        self.status_text.color = ft.Colors.GREEN
        self.filter_variables(None)
        
        # Force UI update
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()

    def filter_variables(self, e):
        """Filter variables based on category and search"""
        category = self.category_filter.value if self.category_filter else "All"
        search_text = self.search_field.value.lower() if self.search_field and self.search_field.value else ""
        
        self.filtered_variables = []
        for var in self.available_variables:
            if category != "All" and var.category != category:
                continue
            if search_text and search_text not in var.name.lower() and search_text not in var.index.lower():
                continue
            self.filtered_variables.append(var)
        
        self.update_variables_list()

    def update_variables_list(self):
        """Update the variables list display"""
        self.variables_list.controls.clear()
        
        for var in self.filtered_variables:
            list_item = ft.ListTile(
                title=ft.Text(var.name, size=13),
                subtitle=ft.Text(f"{var.index} - {var.category} - {var.data_length} bytes", size=12),
                on_click=lambda e, v=var: self.select_variable(v),
                bgcolor=ft.Colors.BLUE_50 if var == self.selected_variable else None
            )
            self.variables_list.controls.append(list_item)  # Agregar el item a la lista
        
        if self.variables_module.page:
            self.variables_module.page.update()
    
    def _add_object_variables(self, obj: Dict[str, Any], category: str):
        """Add object and its sub-objects to available variables - DISABLED for od_c_parser"""
        # This method is not used when working with od_c_parser data
        # od_c_parser only provides simple register entries, not complex objects
        pass

    
    def select_variable(self, variable: TrackedVariable):
        """Select a variable for addition"""
        self.selected_variable = variable
        self.add_button.disabled = False
        self.update_variables_list()
        if self.variables_module.page:
            self.variables_module.page.update()

    def add_selected_variable(self, e):
        """Add selected variable to tracking"""
        if self.selected_variable:
            # Use variables_module reference instead of parent
            if not hasattr(self.variables_module, 'right_panel'):
                if hasattr(self.variables_module, 'logger'):
                    self.variables_module.logger.error(f"Variables module object type: {type(self.variables_module)}")
                else:
                    print(f"Error: Variables module object type: {type(self.variables_module)}")
                return
            
            self.variables_module.right_panel.add_variable(self.selected_variable)
            self.selected_variable = None
            self.add_button.disabled = True
            self.update_variables_list()
