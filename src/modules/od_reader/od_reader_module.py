import flet as ft
from typing import Any
import os
from .panels.left_panel import LeftPanel
from .panels.right_panel import RightPanel
from utils import od_c_parser

class ODReaderModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.registers = []
        self.pdo_mappings = {}  # Store PDO mappings
        self.variables_module = None  # Reference to variables module
        self.monitor_module = None  # Reference to monitor module
        self.graph_module = None  # Reference to graph module

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
                self.load_od_c_file(file_path)

        file_picker = ft.FilePicker(on_result=file_picker_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.pick_files(
            dialog_title="Select OD.c file",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["c"]
        )

    def load_od_c_file(self, file_path: str):
        """Load and parse OD.c file using od_c_parser.py"""
        try:
            # Use centralized parser for variables
            results = od_c_parser.parse_od_c(file_path)
            self.registers = []
            for reg in results:
                # reg should be a dict with index, name, dataLength, category, dataType
                self.registers.append(reg)

            # Extract PDO mappings
            try:
                self.pdo_mappings = od_c_parser.parse_pdo_mappings(file_path)
                self.logger.info(f"Extracted {len(self.pdo_mappings['rpdos'])} RPDOs and {len(self.pdo_mappings['tpdos'])} TPDOs")
            except Exception as e:
                self.logger.warning(f"Could not extract PDO mappings: {e}")
                self.pdo_mappings = {'rpdos': [], 'tpdos': []}

            # Save file path to config
            self.config.od_file_path = file_path
            self.save_path_to_config()

            # Update UI
            self.left_panel.update_file_info(os.path.basename(file_path))
            self.left_panel.update_status("OD.c file loaded successfully", ft.Colors.GREEN)
            self.left_panel.update_summary(len(self.registers))
            self.right_panel.update_content(self.registers)
            
            # Notify variables module if available - with better error handling
            if self.variables_module:
                try:
                    self.logger.info("Notifying variables module of new OD data")
                    self.variables_module.load_od_variables(self)
                    self.logger.info("Successfully notified variables module of new OD data")
                except Exception as e:
                    self.logger.error(f"Error notifying variables module: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.warning("Variables module reference not set")
            
            # Notify monitor module if available
            if self.monitor_module:
                try:
                    self.monitor_module.load_od_data(self)
                    self.logger.info("Notified monitor module of new OD data")
                except Exception as e:
                    self.logger.warning(f"Could not notify monitor module: {e}")
            
            # Notify graph module if available
            if self.graph_module:
                try:
                    self.graph_module.load_od_data(self)
                    self.logger.info("Notified graph module of new OD data")
                except Exception as e:
                    self.logger.warning(f"Could not notify graph module: {e}")

            # Force page update
            if self.page:
                self.page.update()

        except Exception as ex:
            self.logger.error(f"Error loading OD.c file: {ex}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.left_panel.update_status(f"Error loading file: {str(ex)}", ft.Colors.RED)
            if self.page:
                self.page.update()

    def save_configuration(self, e):
        """Save configuration to file"""
        if not self.registers:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("No configuration to save. Please load an OD.c file first."),
                    bgcolor=ft.Colors.RED_400
                )
            )
            return

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
                self.load_od_c_file(self.config.od_file_path)

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
        # For now, we just store it in the config object
        pass

    def get_registers_for_export(self):
        """Get registers list for use by other modules"""
        return self.registers
    
    def set_variables_module(self, variables_module):
        """Set reference to variables module for notifications"""
        self.variables_module = variables_module

    def set_monitor_module(self, monitor_module):
        """Set reference to monitor module for notifications"""
        self.monitor_module = monitor_module
        self.logger.info("Monitor module reference set")
        # If we already have registers loaded, notify the monitor module immediately
        if self.registers:
            try:
                self.monitor_module.load_od_data(self)
                self.logger.info("Loaded existing OD data into monitor module")
            except Exception as e:
                self.logger.warning(f"Could not load existing OD data into monitor module: {e}")

    def set_graph_module(self, graph_module):
        """Set reference to graph module for notifications"""
        self.graph_module = graph_module
        self.logger.info("Graph module reference set")
        # If we already have registers loaded, notify the graph module immediately
        if self.registers:
            try:
                self.graph_module.load_od_data(self)
                self.logger.info("Loaded existing OD data into graph module")
            except Exception as e:
                self.logger.warning(f"Could not load existing OD data into graph module: {e}")

    def get_registers_for_export(self):
        """Get registers list for use by other modules"""
        return self.registers

    def set_variables_module(self, variables_module):
        """Set reference to variables module for notifications"""
        self.variables_module = variables_module

    def get_pdo_mappings(self):
        """Get PDO mappings for use by other modules"""
        return self.pdo_mappings
