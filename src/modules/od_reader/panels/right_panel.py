import flet as ft
from typing import Any, Dict

class RightPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.parser = None
        
        # Parameters tables container
        self.parameters_container = ft.Container(
            content=ft.Text("No data available", size=12, color=ft.Colors.GREY_600),
            alignment=ft.alignment.center
        )
        
        # PDO tables container
        self.pdo_container = ft.Container(
            content=ft.Text("No PDO data available", size=12, color=ft.Colors.GREY_600),
            alignment=ft.alignment.center
        )
    
    def initialize(self):
        """Initialize the right panel"""
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Parameters tables section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Object Dictionary Parameters", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(height=1),
                            ft.Container(
                                content=self.parameters_container,
                            )
                        ], spacing=8)
                    ),
                    
                    ft.Divider(height=1),
                    
                    # PDO mappings section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("PDO Mappings", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(height=1),
                            ft.Container(
                                content=self.pdo_container,
                            )
                        ], spacing=8)
                    )
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                expand=True
            )
        ]
        self.expand = True
    
    def update_content(self, parser):
        """Update content with new parser data"""
        self.parser = parser
        self.parameters_container.content = self.create_parameters_tables()
        self.pdo_container.content = self.create_pdo_tables()
    
    def create_parameters_tables(self) -> ft.Container:
        """Create scrollable tables for manufacturer and device profile parameters"""
        if not self.parser:
            return ft.Container(
                content=ft.Text("No data available", size=12, color=ft.Colors.GREY_600),
                alignment=ft.alignment.center
            )
        
        # Create manufacturer parameters table
        mfg_rows = []
        for index, obj in self.parser.manufacturer_params.items():
            mfg_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(index, size=10)),
                    ft.DataCell(ft.Text(obj.get('name', 'Unknown')[:30], size=10)),
                    ft.DataCell(ft.Text(obj.get('dataType', 'N/A'), size=10)),
                    ft.DataCell(ft.Text(obj.get('accessType', 'N/A'), size=10)),
                    ft.DataCell(ft.Text(obj.get('defaultValue', 'N/A')[:15], size=10)),
                ])
            )
        
        # Create device profile parameters table
        dev_rows = []
        for index, obj in self.parser.device_profile_params.items():
            dev_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(index, size=10)),
                    ft.DataCell(ft.Text(obj.get('name', 'Unknown')[:30], size=10)),
                    ft.DataCell(ft.Text(obj.get('dataType', 'N/A'), size=10)),
                    ft.DataCell(ft.Text(obj.get('accessType', 'N/A'), size=10)),
                    ft.DataCell(ft.Text(obj.get('defaultValue', 'N/A')[:15], size=10)),
                ])
            )
        
        # Add "No data" rows if empty
        if not mfg_rows:
            mfg_rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text("No manufacturer parameters found", size=10)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(""))
            ])]
        
        if not dev_rows:
            dev_rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text("No device profile parameters found", size=10)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(""))
            ])]
        
        return ft.Row([
            # Manufacturer Parameters Table
            ft.Container(
                content=ft.Column([
                    ft.Text("Manufacturer Parameters", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    ft.Container(
                        content=ft.Column([
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Index", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Type", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Access", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Default", size=10, weight=ft.FontWeight.BOLD)),
                                ],
                                rows=mfg_rows,
                                heading_row_height=25,
                                data_row_min_height=20,
                                data_row_max_height=25,
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        height=240
                    )
                ], spacing=5),
                expand=1
            ),
            
            ft.VerticalDivider(width=10),
            
            # Device Profile Parameters Table
            ft.Container(
                content=ft.Column([
                    ft.Text("Device Profile Parameters", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    ft.Container(
                        content=ft.Column([
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Index", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Type", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Access", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Default", size=10, weight=ft.FontWeight.BOLD)),
                                ],
                                rows=dev_rows,
                                column_spacing=8,
                                data_row_max_height=28,
                                heading_row_height=32
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        height=240
                    )
                ], spacing=5),
                expand=1
            )
        ], expand=True)

    def create_pdo_tables(self) -> ft.Container:
        """Create scrollable tables for TPDO and RPDO mappings"""
        if not self.parser:
            return ft.Container(
                content=ft.Text("No PDO data available", size=12, color=ft.Colors.GREY_600),
                alignment=ft.alignment.center
            )
        
        pdo_mappings = self.parser.extract_pdo_mappings()
        
        # Create TPDO table
        tpdo_rows = []
        for pdo_name, mapping in pdo_mappings.get('TPDO', {}).items():
            if mapping['mapped_objects']:
                cob_id = mapping.get('cob_id', 'N/A')
                for i, obj in enumerate(mapping['mapped_objects']):
                    tpdo_rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(pdo_name if i == 0 else "", size=10)),
                            ft.DataCell(ft.Text(cob_id if i == 0 else "", size=10)),
                            ft.DataCell(ft.Text(f"{obj['index']}:{obj['sub_index']}", size=10)),
                            ft.DataCell(ft.Text(obj['name'][:25], size=10)),
                            ft.DataCell(ft.Text(str(obj['length_bits']), size=10)),
                        ])
                    )
        
        # Create RPDO table
        rpdo_rows = []
        for pdo_name, mapping in pdo_mappings.get('RPDO', {}).items():
            if mapping['mapped_objects']:
                cob_id = mapping.get('cob_id', 'N/A')
                for i, obj in enumerate(mapping['mapped_objects']):
                    rpdo_rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(pdo_name if i == 0 else "", size=10)),
                            ft.DataCell(ft.Text(cob_id if i == 0 else "", size=10)),
                            ft.DataCell(ft.Text(f"{obj['index']}:{obj['sub_index']}", size=10)),
                            ft.DataCell(ft.Text(obj['name'][:25], size=10)),
                            ft.DataCell(ft.Text(str(obj['length_bits']), size=10)),
                        ])
                    )
        
        # Add "No data" rows if empty
        if not tpdo_rows:
            tpdo_rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text("No TPDO mappings configured", size=10)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(""))
            ])]
        
        if not rpdo_rows:
            rpdo_rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text("No RPDO mappings configured", size=10)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(""))
            ])]
        
        return ft.Column([
            # TPDO Table
            ft.Container(
                content=ft.Column([
                    ft.Text("Transmit PDOs (TPDO)", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                    ft.Container(
                        content=ft.Column([
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("PDO", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("COB-ID", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Object", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Bits", size=10, weight=ft.FontWeight.BOLD)),
                                ],
                                rows=tpdo_rows,
                                column_spacing=12,
                                data_row_max_height=26,
                                heading_row_height=30
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        border=ft.border.all(1, ft.Colors.BLUE_200),
                        border_radius=5,
                        height=180
                    )
                ], spacing=5)
            ),
            
            ft.Divider(height=8),
            
            # RPDO Table
            ft.Container(
                content=ft.Column([
                    ft.Text("Receive PDOs (RPDO)", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                    ft.Container(
                        content=ft.Column([
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("PDO", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("COB-ID", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Object", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                                    ft.DataColumn(ft.Text("Bits", size=10, weight=ft.FontWeight.BOLD)),
                                ],
                                rows=rpdo_rows,
                                column_spacing=12,
                                data_row_max_height=26,
                                heading_row_height=30
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        border=ft.border.all(1, ft.Colors.GREEN_200),
                        border_radius=5,
                        height=180
                    )
                ], spacing=5)
            )
        ], spacing=8, expand=True)
