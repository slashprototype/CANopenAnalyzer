import flet as ft

class RightPanel(ft.Column):
    def __init__(self, parent_module):
        super().__init__()
        self.parent = parent_module
        self.registers = []

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Index", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Name", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Length (bytes)", size=10, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Category", size=10, weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            heading_row_height=30,
            data_row_min_height=25,
            data_row_max_height=30
        )

    def initialize(self):
        """Initialize the right panel"""
        self.controls = [
            ft.Text("Object Dictionary Registers", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO),
                expand=True,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=10
            )
        ]
        self.expand = True

    def update_content(self, registers):
        """Update table with new registers"""
        self.registers = registers or []
        self.table.rows.clear()
        
        for reg in self.registers:
            self.table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(reg['index'], size=10)),
                    ft.DataCell(ft.Text(reg['name'], size=10)),
                    ft.DataCell(ft.Text(str(reg['data_length']), size=10)),
                    ft.DataCell(ft.Text(reg['category'], size=10)),
                ])
            )
        
        if hasattr(self.parent, 'page') and self.parent.page:
            self.parent.page.update()
    
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
                    ft.DataCell(ft.Text(obj.get('data_type', 'N/A'), size=10)),
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
                    ft.DataCell(ft.Text(obj.get('data_type', 'N/A'), size=10)),
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
        
        try:
            pdo_mappings = self.parser.extract_pdo_mappings() or {'TPDO': {}, 'RPDO': {}}
            
            # Create TPDO table
            tpdo_rows = []
            for pdo_name, mapping in pdo_mappings.get('TPDO', {}).items():
                if not mapping:  # Skip if mapping is None or empty
                    continue
                mapped_objects = mapping.get('mapped_objects', [])
                if mapped_objects:
                    cob_id = mapping.get('cob_id', 'N/A')
                    for i, obj in enumerate(mapped_objects):
                        if not obj:  # Skip if obj is None
                            continue
                        # Safely handle potential None values
                        definitive_size = obj.get('definitive_size_bits', 'N/A')
                        length_bits = obj.get('length_bits', 'N/A')
                        data_source = "XML"
                        
                        # Check if size comes from OD.c
                        if obj.get('od_c_length') is not None:
                            data_source = "OD.c"
                        
                        tpdo_rows.append(
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text(pdo_name if i == 0 else "", size=10)),
                                ft.DataCell(ft.Text(cob_id if i == 0 else "", size=10)),
                                ft.DataCell(ft.Text(f"{obj.get('index', 'N/A')}:{obj.get('sub_index', 'N/A')}", size=10)),
                                ft.DataCell(ft.Text(obj.get('name', 'Unknown')[:25], size=10)),
                                ft.DataCell(ft.Text(str(length_bits), size=10)),
                                ft.DataCell(ft.Text(str(definitive_size), size=10, 
                                        color=ft.Colors.GREEN if data_source == "OD.c" else ft.Colors.BLUE)),
                                ft.DataCell(ft.Text(data_source, size=10, 
                                        color=ft.Colors.GREEN if data_source == "OD.c" else ft.Colors.BLUE)),
                            ])
                        )
            
            # Create RPDO table
            rpdo_rows = []
            for pdo_name, mapping in pdo_mappings.get('RPDO', {}).items():
                if not mapping:  # Skip if mapping is None or empty
                    continue
                mapped_objects = mapping.get('mapped_objects', [])
                if mapped_objects:
                    cob_id = mapping.get('cob_id', 'N/A')
                    for i, obj in enumerate(mapped_objects):
                        if not obj:  # Skip if obj is None
                            continue
                        # Safely handle potential None values
                        definitive_size = obj.get('definitive_size_bits', 'N/A')
                        length_bits = obj.get('length_bits', 'N/A')
                        data_source = "XML"
                        
                        # Check if size comes from OD.c
                        if obj.get('od_c_length') is not None:
                            data_source = "OD.c"
                            
                        rpdo_rows.append(
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text(pdo_name if i == 0 else "", size=10)),
                                ft.DataCell(ft.Text(cob_id if i == 0 else "", size=10)),
                                ft.DataCell(ft.Text(f"{obj.get('index', 'N/A')}:{obj.get('sub_index', 'N/A')}", size=10)),
                                ft.DataCell(ft.Text(obj.get('name', 'Unknown')[:25], size=10)),
                                ft.DataCell(ft.Text(str(length_bits), size=10)),
                                ft.DataCell(ft.Text(str(definitive_size), size=10, 
                                        color=ft.Colors.GREEN if data_source == "OD.c" else ft.Colors.BLUE)),
                                ft.DataCell(ft.Text(data_source, size=10, 
                                        color=ft.Colors.GREEN if data_source == "OD.c" else ft.Colors.BLUE)),
                            ])
                        )
            
            # Add "No data" rows if empty
            if not tpdo_rows:
                tpdo_rows = [ft.DataRow(cells=[
                    ft.DataCell(ft.Text("No TPDO mappings configured", size=10)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
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
                                        ft.DataColumn(ft.Text("Def. Size", size=10, weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Source", size=10, weight=ft.FontWeight.BOLD)),
                                    ],
                                    rows=tpdo_rows,
                                    column_spacing=10,
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
                                        ft.DataColumn(ft.Text("Def. Size", size=10, weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Source", size=10, weight=ft.FontWeight.BOLD)),
                                    ],
                                    rows=rpdo_rows,
                                    column_spacing=10,
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
        except Exception as e:
            print(f"Error creating PDO tables: {e}")
            # Return an error message container
            return ft.Container(
                content=ft.Column([
                    ft.Text("Error displaying PDO data", size=12, color=ft.Colors.RED_600),
                    ft.Text(f"Details: {str(e)}", size=10, color=ft.Colors.RED_400)
                ]),
                alignment=ft.alignment.center
            )
            return ft.Container(
                content=ft.Column([
                    ft.Text("Error displaying PDO data", size=12, color=ft.Colors.RED_600),
                    ft.Text(f"Details: {str(e)}", size=10, color=ft.Colors.RED_400)
                ]),
                alignment=ft.alignment.center
            )
