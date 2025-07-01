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
        
        # UI components
        self.variables_list = None
        
    def initialize_ui(self):
        """Initialize the variables list UI"""
        self.variables_list = ft.Column([
            ft.Text("Available PDO Variables", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("Select variables to graph:", size=12),
        ], scroll=ft.ScrollMode.AUTO)
        
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
            
            # Get variable names from OD registers (only manufacturer category)
            manufacturer_vars = {}
            for reg in self.od_registers:
                if reg.get('category') == 'Manufacturer':
                    manufacturer_vars[reg['index']] = reg.get('name', 'Unknown')
            
            self.logger.info(f"Found {len(manufacturer_vars)} manufacturer variables in OD")
            
            # Add manufacturer variables that are mapped in PDOs
            variables_added = 0
            for cob_id, pdo_info in cob_id_to_pdo.items():
                pdo_data = pdo_info['pdo_info']
                pdo_type = pdo_info['type']
                
                self.logger.debug(f"Processing {pdo_type} with COB-ID 0x{cob_id:03X}, variables: {len(pdo_data.get('mapped_variables', []))}")
                
                for var in pdo_data.get('mapped_variables', []):
                    var_index = var['index']
                    
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
                        
                        # Create draggable variable item
                        draggable_var = ft.Draggable(
                            group="variables",
                            content=ft.Container(
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
                                width=250
                            ),
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
                            data=var_index  # Pass the variable index directly
                        )
                        
                        self.variables_list.controls.append(draggable_var)
                        variables_added += 1
                        
                        self.logger.debug(f"Added variable {var_index} - {var_name}")
            
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
            
            if self.page:
                self.page.update()
                
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
