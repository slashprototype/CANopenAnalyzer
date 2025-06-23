import flet as ft
from typing import Any, Dict
from .tracked_variable import TrackedVariable

class LeftPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.variables_module = parent_module  # Keep separate reference to avoid Flet overwriting
        self.available_variables = []
        self.filtered_variables = []
        self.selected_variable = None
        
        # Controls
        self.category_filter = None
        self.search_field = None
        self.variables_list = None
        self.add_button = None
        self.status_text = None
        self.load_od_button = None
        self.refresh_button = None
    
    def initialize(self):
        """Initialize the left panel"""
        self.category_filter = ft.Dropdown(
            label="Category Filter",
            options=[
                ft.dropdown.Option("All"),
                ft.dropdown.Option("Communication"),
                ft.dropdown.Option("Manufacturer"),
                ft.dropdown.Option("Device Profile")
            ],
            value="All",
            on_change=self.filter_variables,
            width=200
        )
        
        self.search_field = ft.TextField(
            label="Search variables",
            hint_text="Enter variable name or index",
            on_change=self.filter_variables,
            width=200
        )
        
        self.variables_list = ft.ListView(
            height=300,
            spacing=2
        )
        
        self.add_button = ft.ElevatedButton(
            "Add Variable",
            icon=ft.Icons.ADD,
            on_click=self.add_selected_variable,
            disabled=True
        )
        
        # New buttons for OD management
        self.load_od_button = ft.ElevatedButton(
            "Load OD File",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.load_od_file,
            tooltip="Load Object Dictionary XML file independently"
        )
        
        self.refresh_button = ft.ElevatedButton(
            "Refresh from OD Reader",
            icon=ft.Icons.REFRESH,
            on_click=self.refresh_from_od_reader,
            tooltip="Load variables from OD Reader module"
        )
        
        self.status_text = ft.Text(
            "Load OD file to see variables",
            size=12,
            color=ft.Colors.GREY_600
        )
        
        self.controls = [
            ft.Text("Variable Selection", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            
            # OD Management buttons
            ft.Row([
                self.load_od_button,
                self.refresh_button
            ], spacing=5),
              ft.Divider(height=1),
            
            # Arrange filter and search in the same row
            ft.Row([
                self.category_filter,
                self.search_field
            ], spacing=10),
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
    
    def load_od_file(self, e):
        """Load OD file independently"""
        def file_picker_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                self.load_xml_file_directly(file_path)
        
        file_picker = ft.FilePicker(on_result=file_picker_result)
        self.variables_module.page.overlay.append(file_picker)
        self.variables_module.page.update()
        
        file_picker.pick_files(
            dialog_title="Select Object Dictionary XML file",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xml"]
        )
    
    def load_xml_file_directly(self, file_path: str):
        """Load XML file directly in variables module"""
        try:
            from utils.od_xml_parser import ODXMLParser
            import os
            
            self.status_text.value = "Loading XML file..."
            self.status_text.color = ft.Colors.ORANGE
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.update()
            
            # Parse XML file
            parser = ODXMLParser(file_path)
            
            # Create a mock od_module object
            class MockODModule:
                def __init__(self, parser):
                    self.parser = parser
            
            mock_od_module = MockODModule(parser)
            self.load_variables_from_od(mock_od_module)
            
            self.status_text.value = f"Loaded from: {os.path.basename(file_path)}"
            self.status_text.color = ft.Colors.GREEN
            
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.open(
                    ft.SnackBar(
                        content=ft.Text(f"Successfully loaded OD from {os.path.basename(file_path)}"),
                        bgcolor=ft.Colors.GREEN_400
                    )
                )
            
        except Exception as e:
            if hasattr(self.variables_module, 'logger'):
                self.variables_module.logger.error(f"Error loading XML file directly: {e}")
            else:
                print(f"Error loading XML file directly: {e}")
            
            self.status_text.value = f"Error loading file: {str(e)}"
            self.status_text.color = ft.Colors.RED
            
            if hasattr(self.variables_module, 'page') and self.variables_module.page:
                self.variables_module.page.open(
                    ft.SnackBar(
                        content=ft.Text(f"Error loading OD file: {str(e)}"),
                        bgcolor=ft.Colors.RED_400
                    )
                )
        
        if hasattr(self.variables_module, 'page') and self.variables_module.page:
            self.variables_module.page.update()
    
    def refresh_from_od_reader(self, e):
        """Refresh variables from OD Reader module"""
        try:
            # Try to get OD reader module from parent
            od_module = self.variables_module.get_od_reader_module()
            
            if od_module and od_module.parser:
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
                            content=ft.Text("No OD data available. Load an OD file in OD Reader module first."),
                            bgcolor=ft.Colors.ORANGE_400
                        )
                    )
                
        except Exception as e:
            if hasattr(self.variables_module, 'logger'):
                self.variables_module.logger.error(f"Error refreshing from OD reader: {e}")
            else:
                print(f"Error refreshing from OD reader: {e}")
            
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
    
    def load_variables_from_od(self, od_module):
        """Load variables from OD reader module"""
        try:
            if not od_module or not od_module.parser:
                self.status_text.value = "No OD data available"
                self.status_text.color = ft.Colors.RED
                return
                
            self.available_variables.clear()
            parser = od_module.parser
            
            # Load communication parameters
            for index, obj in parser.communication_params.items():
                self._add_object_variables(obj, "Communication")
            
            # Load manufacturer parameters
            for index, obj in parser.manufacturer_params.items():
                self._add_object_variables(obj, "Manufacturer")
                
            # Load device profile parameters
            for index, obj in parser.device_profile_params.items():
                self._add_object_variables(obj, "Device Profile")
            
            self.status_text.value = f"Loaded {len(self.available_variables)} variables"
            self.status_text.color = ft.Colors.GREEN
            self.filter_variables(None)
            
        except Exception as e:
            if hasattr(self.variables_module, 'logger'):
                self.variables_module.logger.error(f"Error loading variables from OD: {e}")
            else:
                print(f"Error loading variables from OD: {e}")
            self.status_text.value = f"Error loading variables: {str(e)}"
            self.status_text.color = ft.Colors.RED
    
    def _add_object_variables(self, obj: Dict[str, Any], category: str):
        """Add object and its sub-objects to available variables"""
        # Main object
        if obj.get('dataType') and obj.get('dataType') != 'RECORD':
            var = TrackedVariable(
                index=obj['index'],
                sub_index="00",
                name=obj['name'],
                category=category,
                data_type=obj.get('dataType', 'Unknown')
            )
            self.available_variables.append(var)
        
        # Sub-objects
        for sub_obj in obj.get('subObjects', []):
            if sub_obj.get('dataType'):
                var = TrackedVariable(
                    index=obj['index'],
                    sub_index=sub_obj['subIndex'],
                    name=sub_obj['name'],
                    category=category,
                    data_type=sub_obj.get('dataType', 'Unknown')
                )
                self.available_variables.append(var)
    
    def filter_variables(self, e):
        """Filter variables based on category and search"""
        category = self.category_filter.value if self.category_filter else "All"
        search_text = self.search_field.value.lower() if self.search_field and self.search_field.value else ""
        
        self.filtered_variables = []
        for var in self.available_variables:
            # Category filter
            if category != "All" and var.category != category:
                continue
                
            # Search filter
            if search_text and search_text not in var.name.lower() and search_text not in var.index.lower():
                continue
                
            self.filtered_variables.append(var)
        
        self.update_variables_list()
    
    def update_variables_list(self):
        """Update the variables list display"""
        self.variables_list.controls.clear()
        
        for var in self.filtered_variables:
            list_item = ft.ListTile(
                title=ft.Text(var.name, size=12),
                subtitle=ft.Text(f"{var.index}:{var.sub_index} - {var.category} - {var.data_type}", size=10),
                on_click=lambda e, v=var: self.select_variable(v),
                bgcolor=ft.Colors.BLUE_50 if var == self.selected_variable else None
            )
            self.variables_list.controls.append(list_item)
        
        if self.variables_module.page:
            self.variables_module.page.update()
    
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
