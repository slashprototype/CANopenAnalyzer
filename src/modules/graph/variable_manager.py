import flet as ft
from typing import Dict, Set, List

class VariableManager:
    def __init__(self, logger, page):
        self.logger = logger
        self.page = page
        
        # Variable data
        self.od_registers = []
        self.pdo_variables = {}
        self.selected_variables = set()  # Variables selected for graphing
        
        # Track draggable controls for drop event handling
        self.draggable_control_map = {}  # {control_id: variable_index}
        
        # UI components
        self.variables_list = None
    
    def initialize_ui(self):
        """Initialize the variables list UI"""
        self.variables_list = ft.Column([
            ft.Text("Available PDO Variables", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("Select variables to graph:", size=12),
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        return self.variables_list
    
    def load_od_data(self, od_module):
        """Load OD data from OD reader module"""
        try:
            # Load OD registers
            self.od_registers = []
            
            if not hasattr(od_module, 'registers') or not od_module.registers:
                self.logger.warning("No registers found in OD module")
                return
            
            for reg in od_module.registers:
                reg_copy = dict(reg)
                if "dataLength" in reg_copy:
                    reg_copy["data_length"] = reg_copy.pop("dataLength")
                self.od_registers.append(reg_copy)
            
            self.logger.info(f"Loaded {len(self.od_registers)} OD registers in Variable Manager")
            
            # Log some details for debugging
            manufacturer_count = len([r for r in self.od_registers if r.get('category') == 'Manufacturer'])
            self.logger.info(f"Found {manufacturer_count} manufacturer variables")
            
        except Exception as e:
            self.logger.error(f"Error loading OD data in Variable Manager: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def build_variables_list(self, cob_id_to_pdo, data_collector):
        """Build the variables list with drag and drop support for selection"""
        try:
            self.logger.info(f"Building variables list with {len(cob_id_to_pdo)} PDO mappings")
            
            # Clear existing content except headers
            self.variables_list.controls = self.variables_list.controls[:2]
            self.pdo_variables = {}
            self.draggable_control_map = {}  # Clear the mapping
            
            # Get variable names from OD registers (only manufacturer category)
            manufacturer_vars = {}
            for reg in self.od_registers:
                if reg.get('category') == 'Manufacturer':
                    manufacturer_vars[reg['index']] = reg.get('name', 'Unknown')
                    # Debug: Log each manufacturer variable found
                    self.logger.debug(f"Found manufacturer variable: {reg['index']} - {reg.get('name', 'Unknown')}")
            
            self.logger.info(f"Found {len(manufacturer_vars)} manufacturer variables in OD")
            self.logger.debug(f"Manufacturer variables indices: {list(manufacturer_vars.keys())}")
            
            # Add manufacturer variables that are mapped in PDOs
            variables_added = 0
            for cob_id, pdo_info in cob_id_to_pdo.items():
                pdo_data = pdo_info['pdo_info']
                pdo_type = pdo_info['type']
                
                self.logger.debug(f"Processing {pdo_type} with COB-ID 0x{cob_id:03X}, variables: {len(pdo_data.get('mapped_variables', []))}")
                
                for var in pdo_data.get('mapped_variables', []):
                    var_index = var['index']
                    self.logger.debug(f"Processing PDO variable with index: {var_index} (type: {type(var_index)})")
                    
                    # Only include manufacturer variables
                    if var_index in manufacturer_vars:
                        var_name = manufacturer_vars[var_index]
                        
                        # Store variable info
                        self.pdo_variables[var_index] = {
                            'name': var_name,
                            'cob_id': f"0x{cob_id:03X}",
                            'type': pdo_type,
                            'bits': var['bit_length'],
                            'current_value': 'No data'
                        }
                        
                        # Initialize history in data collector
                        data_collector.initialize_variable_history(var_index)
                        
                        # Create draggable variable item with proper data handling
                        draggable_content = ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DRAG_INDICATOR, size=16, color=ft.Colors.BLUE_400),
                                ft.Column([
                                    ft.Text(f"{var_index} - {var_name[:25]}", size=11, weight=ft.FontWeight.W_500),
                                    ft.Text(f"({pdo_type})", size=9, color=ft.Colors.GREY_600)
                                ], spacing=2)
                            ], tight=True),
                            padding=8,
                            border_radius=4,
                            bgcolor=ft.Colors.BLUE_50,
                            border=ft.border.all(1, ft.Colors.BLUE_200),
                            width=250,
                            data=var_index  # Store variable index in container data
                        )
                        
                        draggable_var = ft.Draggable(
                            group="variables",
                            content=draggable_content,
                            content_feedback=ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.MOVING, size=14),
                                    ft.Text(f"{var_index}", size=10, weight=ft.FontWeight.BOLD)
                                ], tight=True),
                                padding=8,
                                bgcolor=ft.Colors.BLUE_100,
                                border_radius=4,
                                border=ft.border.all(2, ft.Colors.BLUE_400),
                                opacity=0.8
                            ),
                            data=var_index  # Store variable index in draggable data
                        )
                        
                        # Store the mapping for later retrieval during drop events
                        # We'll store it when the control gets an ID assigned by Flet
                        if hasattr(draggable_var, 'uid'):
                            self.draggable_control_map[draggable_var.uid] = var_index
                        
                        # Debug print to verify variable index
                        self.logger.info(f"Created draggable for variable: '{var_index}' with data: '{var_index}' - {var_name}")
                        
                        self.variables_list.controls.append(draggable_var)
                        variables_added += 1
                        
                        self.logger.debug(f"Added variable {var_index} - {var_name}")
                    else:
                        self.logger.debug(f"Variable {var_index} not found in manufacturer variables list")
            
            # Update data collector's pdo_variables reference
            data_collector.pdo_variables = self.pdo_variables
            
            self.logger.info(f"Successfully added {variables_added} variables to the list")
            
            # Add a message if no variables were found
            if variables_added == 0:
                self.variables_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "No manufacturer variables found in PDO mappings.\n\n"
                            "Make sure:\n"
                            "• OD file is loaded\n"
                            "• PDO mappings exist\n"
                            "• Variables are marked as 'Manufacturer' category",
                            text_align=ft.TextAlign.CENTER,
                            size=10,
                            color=ft.Colors.ORANGE_600
                        ),
                        padding=10,
                        bgcolor=ft.Colors.ORANGE_50,
                        border_radius=4,
                        border=ft.border.all(1, ft.Colors.ORANGE_200)
                    )
                )
            
            # Force update of the variables list
            if hasattr(self.variables_list, 'update'):
                self.variables_list.update()
                
            # Force page update
            if self.page and hasattr(self.page, 'update'):
                try:
                    self.page.update()
                except Exception as page_error:
                    self.logger.debug(f"Page update failed in variables list: {page_error}")
                
        except Exception as e:
            self.logger.error(f"Error building variables list: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def get_selected_variables_data(self, data_collector) -> Dict[str, List]:
        """Get data for all selected variables"""
        return {var_index: data_collector.get_variable_data(var_index) 
                for var_index in self.selected_variables}
    
    def get_variable_count(self) -> int:
        """Get total number of available variables"""
        return len(self.pdo_variables)
    
    def get_selected_count(self) -> int:
        """Get number of selected variables"""
        return len(self.selected_variables)
    
    def get_selected_variables(self):
        """Get list of selected variables"""
        # Return empty list for now - this will be implemented based on your UI selection logic
        return []
