import flet as ft
from typing import Any, Dict, List
import os
from utils.od_xml_parser import ODXMLParser
from classes.xml_register import XMLRegister
from .panels.left_panel import LeftPanel
from .panels.right_panel import RightPanel

class ODReaderModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.parser = None
        self.registers = []
        self.variables_module = None  # Reference to variables module
        
        # Create panels
        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)
        
    def initialize(self):
        """Initialize the OD reader module"""
        self.controls = [
            ft.Container(
                content=ft.Row([
                    # Left panel (33%)
                    ft.Container(
                        content=self.left_panel,
                        width=None,
                        expand=1
                    ),
                    
                    ft.VerticalDivider(width=1),
                    
                    # Right panel (67%)
                    ft.Container(
                        content=self.right_panel,
                        width=None,
                        expand=3,
                        padding=ft.padding.only(left=10)
                    )
                ], expand=True),
                padding=20,
                expand=True
            )
        ]
        self.expand = True
        
        # Initialize panels
        self.left_panel.initialize()
        self.right_panel.initialize()
        
        # Load saved OD file path if exists
        self.load_saved_path()
    
    def load_od_file(self, e):
        """Handle OD file loading"""
        def file_picker_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                self.load_xml_file(file_path)
        
        file_picker = ft.FilePicker(on_result=file_picker_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        
        file_picker.pick_files(
            dialog_title="Select Object Dictionary XML file",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xml"]
        )
    
    def load_xml_file(self, file_path: str):
        """Load and parse XML file"""
        try:
            self.left_panel.update_status("Loading XML file...", ft.Colors.ORANGE)
            self.page.update()
            
            # Parse XML file
            self.parser = ODXMLParser(file_path)
            
            # Save file path to config
            self.config.od_file_path = file_path
            self.save_path_to_config()
            
            # Update UI
            self.left_panel.update_file_info(os.path.basename(file_path))
            self.left_panel.update_status("XML file loaded successfully", ft.Colors.GREEN)
            
            # Create registers
            self.create_registers()
            
            # Update panels
            self.left_panel.update_summary(self.parser.get_summary())
            self.right_panel.update_content(self.parser)
            
            # Notify variables module if available
            if self.variables_module:
                try:
                    self.variables_module.load_od_variables(self)
                    self.logger.info("Notified variables module of new OD data")
                except Exception as e:
                    self.logger.warning(f"Could not notify variables module: {e}")
            
            self.page.update()
            
        except Exception as ex:
            self.logger.error(f"Error loading XML file: {ex}")
            self.left_panel.update_status(f"Error loading file: {str(ex)}", ft.Colors.RED)
            self.page.update()

    def create_registers(self):
        """Create register objects from parsed XML"""
        self.registers = []
        
        try:
            # Create registers for all objects
            for index, obj_data in self.parser.objects.items():
                # Main object
                register = XMLRegister(index, obj_data)
                self.registers.append(register)
                
                # Sub-objects
                sub_objects = obj_data.get('subObjects', [])
                if sub_objects:
                    for sub_obj in sub_objects:
                        sub_index = sub_obj.get('subIndex')
                        if sub_index:  # Only create register if sub_index exists
                            sub_register = XMLRegister(index, sub_obj, sub_index)
                            self.registers.append(sub_register)
            
            # Update PDO mappings
            pdo_mappings = self.parser.extract_pdo_mappings()
            self.update_pdo_registers(pdo_mappings)
            
        except Exception as e:
            self.logger.error(f"Error creating registers: {e}")
            raise
    
    def update_pdo_registers(self, pdo_mappings: Dict[str, Any]):
        """Update registers with PDO mapping information"""
        try:
            for pdo_type, mappings in pdo_mappings.items():
                for pdo_name, mapping_data in mappings.items():
                    cob_id = mapping_data.get('cob_id', '')
                    if cob_id:
                        # Extract COB-ID value
                        try:
                            if '$NODEID' in cob_id:
                                # Handle node ID substitution (assume node ID 1 for now)
                                cob_id = cob_id.replace('$NODEID', '0x01')
                            cob_id_value = int(cob_id, 16) & 0x7FF  # Extract 11-bit CAN ID
                        except (ValueError, TypeError):
                            cob_id_value = 0
                        
                        # Update corresponding registers
                        mapped_objects = mapping_data.get('mapped_objects', [])
                        for pos, mapped_obj in enumerate(mapped_objects):
                            obj_index = mapped_obj.get('index')
                            obj_sub_index = mapped_obj.get('sub_index')
                            
                            if obj_index:  # Only process if index exists
                                # Find and update register
                                for register in self.registers:
                                    if (register.index == obj_index and 
                                        register.sub_index == obj_sub_index):
                                        register.cob_id = f"{cob_id_value:03X}"
                                        register.position = pos
                                        register.pdo_type = pdo_type
                                        break
        except Exception as e:
            self.logger.error(f"Error updating PDO registers: {e}")

    def save_configuration(self, e):
        """Save configuration to file"""
        if not self.parser:
            # Show snackbar with error
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("No configuration to save. Please load an OD XML file first."),
                    bgcolor=ft.Colors.RED_400
                )
            )
            return
        
        # Show success message
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text("Configuration saved successfully!"),
                bgcolor=ft.Colors.GREEN_400
            )
        )

    def load_saved_path(self):
        """Load saved OD file path from config"""
        if hasattr(self.config, 'od_file_path') and self.config.od_file_path:
            if os.path.exists(self.config.od_file_path):
                self.load_xml_file(self.config.od_file_path)
    
    def save_path_to_config(self):
        """Save OD file path to config"""
        # This would typically save to a config file
        # For now, we just store it in the config object
        pass

    def get_registers_for_export(self):
        """Get registers list for use by other modules"""
        return self.registers
    
    def set_variables_module(self, variables_module):
        """Set reference to variables module for notifications"""
        self.variables_module = variables_module
