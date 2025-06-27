import flet as ft
import threading
import time
from typing import Any, List, Optional, Dict
from datetime import datetime

from interfaces import InterfaceManager, CANMessage

class MonitorModule(ft.Column):
    def __init__(self, page: ft.Page, config: Any, logger: Any, interface_manager: InterfaceManager = None):
        super().__init__()
        self.page = page
        self.config = config
        self.logger = logger
        self.is_monitoring = False
        self.message_list = []
        self.message_table = None
        self.pdo_variables_table = None  # New PDO variables table
        self.control_buttons = None
        # Use singleton instance
        self.interface_manager = interface_manager or InterfaceManager.get_instance()
        self.od_reader_module = None  # Reference to OD reader module
        self.od_registers = []  # Store OD registers for message interpretation
        self.pdo_mappings = {}  # Store PDO mappings
        self.pdo_variables = {}  # Store current PDO variable values {index: value}
        self.cob_id_to_pdo = {}  # Map COB-ID to PDO info for quick lookup
        self.stats_controls = {}
        self.filter_node_id = None
        self.selected_node_id = 0  # Node ID selected from dropdown
        self.message_count = 0
        self.error_count = 0
        self.last_update_time = time.time()
        self.messages_since_last_update = 0
        
    def initialize(self):
        """Initialize the monitor module"""
        # Register for connection state changes
        self.interface_manager.add_connection_callback(self.update_connection_status)
        
        # Don't initialize interface manager here if one was provided
        if self.interface_manager and not self.interface_manager.current_interface:
            if not self.interface_manager.initialize_interface():
                self.logger.error("Failed to initialize CAN interface")
        
        # Create message table
        self.message_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Time", size=12)),
                ft.DataColumn(ft.Text("COB-ID", size=12)),
                ft.DataColumn(ft.Text("Node", size=12)),
                ft.DataColumn(ft.Text("Type", size=12)),
                ft.DataColumn(ft.Text("Data", size=12)),
                ft.DataColumn(ft.Text("Len", size=12))
            ],
            rows=[],
            heading_row_height=30,
            data_row_min_height=25,
            data_row_max_height=25,
        )
        
        # Create PDO variables table for manufacturer registers
        self.pdo_variables_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Index", size=12)),
                ft.DataColumn(ft.Text("Variable Name", size=12)),
                ft.DataColumn(ft.Text("Value", size=12)),
                ft.DataColumn(ft.Text("COB-ID", size=12)),
                ft.DataColumn(ft.Text("Updated", size=12))
            ],
            rows=[],
            heading_row_height=30,
            data_row_min_height=25,
            data_row_max_height=25,
        )
        
        self.build_interface()
    
    def build_interface(self):
        """Build the monitor interface with two tables side by side"""
        # Control buttons

        # Statistics
        self.stats_controls = {
            "msg_count": ft.Text("Messages: 0", size=12),
            "error_count": ft.Text("Errors: 0", size=12),
            "rate": ft.Text("Rate: 0 msg/s", size=12),
            "pdo_count": ft.Text("PDO Variables: 0", size=12),
            "interface_status": ft.Text("Status: Disconnected", color=ft.Colors.RED, size=12)
        }
        
        stats = ft.Row([
            self.stats_controls["msg_count"],
            self.stats_controls["error_count"],
            self.stats_controls["rate"],
            self.stats_controls["pdo_count"],
            ft.Container(expand=True),
            self.stats_controls["interface_status"]
        ])

        self.control_buttons = ft.Row([
            ft.ElevatedButton(
                "Start Monitor",
                icon=ft.Icons.PLAY_ARROW,
                on_click=self.start_monitoring,
                disabled=not self.interface_manager.is_connected(),
                height=35
            ),
            ft.ElevatedButton(
                "Stop Monitor",
                icon=ft.Icons.STOP,
                on_click=self.stop_monitoring,
                disabled=True,
                height=35
            ),
            ft.ElevatedButton(
                "Clear",
                icon=ft.Icons.CLEAR,
                on_click=self.clear_messages,
                height=35
            ),
            stats,
            ft.Container(expand=True),
            ft.Text("Filter Node ID:", size=12),
            ft.TextField(
                width=80,
                height=35,
                hint_text="All",
                on_change=self.filter_messages,
                text_size=12
            ),
            ft.Text("Selected Node ID:", size=12),
            ft.TextField(
                width=80,
                height=35,
                hint_text="0",
                on_change=self.select_node_id,
                text_size=12
            ),

        ])
        # Create two-column layout for tables
        tables_row = ft.Row([
            # Left side - CAN Messages (60%)
            ft.Container(
                content=ft.Column([
                    ft.Text("CAN Messages", size=14, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            self.message_table
                        ], scroll=ft.ScrollMode.AUTO),
                        expand=True,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5
                    )
                ]),
                expand=3,
                padding=ft.padding.only(right=5)
            ),
            
            # Right side - PDO Variables (40%)
            ft.Container(
                content=ft.Column([
                    ft.Text("Manufacturer Variables (PDO)", size=14, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([
                            self.pdo_variables_table
                        ], scroll=ft.ScrollMode.AUTO),
                        expand=True,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5
                    )
                ]),
                expand=2,
                padding=ft.padding.only(left=5)
            )
        ], expand=True)
        
        # Build main layout
        self.controls = [
            ft.Container(
                content=self.control_buttons,
                padding=8
            ),
            # ft.Container(
            #     content=stats,
            #     padding=8,
            #     bgcolor=ft.Colors.GREY_50,
            #     border_radius=5
            # ),
            tables_row
        ]
        
        self.expand = True
    
    def start_monitoring(self, e):
        """Start CAN message monitoring"""
        try:
            if not self.interface_manager or not self.interface_manager.is_connected():
                self.logger.error("Cannot start monitoring - interface not connected")
                return
            
            # Clear existing messages for a clean start
            self.message_list.clear()
            self.message_table.rows.clear()
            self.message_count = 0
            self.error_count = 0
            self.messages_since_last_update = 0
            self.last_update_time = time.time()
            
            # Add message callback
            self.interface_manager.add_message_callback(self.on_message_received)
            
            # Start monitoring
            if self.interface_manager.start_monitoring():
                self.is_monitoring = True
                self.update_button_states()
                self.start_stats_update()
                self.logger.info("Started CAN message monitoring")
            else:
                self.logger.error("Failed to start monitoring")
            
            self.page.update()
        except Exception as ex:
            self.logger.error(f"Error starting monitoring: {ex}")
    
    def stop_monitoring(self, e):
        """Stop CAN message monitoring"""
        try:
            if self.interface_manager:
                self.interface_manager.stop_monitoring()
                # Remove message callback
                self.interface_manager.remove_message_callback(self.on_message_received)
            
            self.is_monitoring = False
            self.update_button_states()
            self.logger.info("Stopped CAN message monitoring")
            self.page.update()
        except Exception as ex:
            self.logger.error(f"Error stopping monitoring: {ex}")
    
    def clear_messages(self, e):
        """Clear message history and reset PDO variables"""
        self.message_list.clear()
        self.message_table.rows.clear()
        
        # Reset PDO variable values
        for var_index in self.pdo_variables:
            self.pdo_variables[var_index]['value'] = 'No data'
            self.pdo_variables[var_index]['last_update'] = 'Never'
        self.update_pdo_variables_table()
        
        self.message_count = 0
        self.error_count = 0
        self.update_statistics()
        self.page.update()
        self.logger.info("Message history and PDO variables cleared")
    
    def select_node_id(self, e):
        """Handle selection of node ID from dropdown"""
        try:
            selected_value = e.control.value.strip()
            if selected_value == "":
                self.selected_node_id = 0
            else:
                self.selected_node_id = int(selected_value)
            
            self.logger.info(f"Node ID selected in monitoring: {self.selected_node_id}")
        except ValueError:
            self.logger.warning(f"Invalid node ID selected: {e.control.value}")
    
    def filter_messages(self, e):
        """Filter messages by node ID"""
        try:
            filter_text = e.control.value.strip()
            if filter_text == "" or filter_text.lower() == "all":
                self.filter_node_id = None
            else:
                self.filter_node_id = int(filter_text)
            
            self.rebuild_message_table()
            self.logger.info(f"Message filter set to node ID: {self.filter_node_id}")
        except ValueError:
            self.logger.warning(f"Invalid node ID filter: {e.control.value}")
    
    def auto_load_from_od_reader(self):
        """Automatically load OD data from OD reader if available"""
        try:
            od_module = self.get_od_reader_module()
            if od_module and hasattr(od_module, "registers") and od_module.registers:
                # Store registers for message interpretation
                self.od_registers = []
                for reg in od_module.registers:
                    reg_copy = dict(reg)
                    if "dataLength" in reg_copy:
                        reg_copy["data_length"] = reg_copy.pop("dataLength")
                    self.od_registers.append(reg_copy)
                
                self.logger.info(f"Loaded {len(self.od_registers)} OD registers for message interpretation")
        except Exception as e:
            self.logger.debug(f"Could not auto-load from OD reader: {e}")
    
    def get_od_reader_module(self):
        """Get reference to OD reader module from main app"""
        return self.od_reader_module
    
    def set_od_reader_module(self, od_reader_module):
        """Set reference to OD reader module"""
        self.od_reader_module = od_reader_module
        # Try to load OD data immediately if registers are available
        if od_reader_module and hasattr(od_reader_module, "registers") and od_reader_module.registers:
            self.load_od_data(od_reader_module)
    
    def load_od_data(self, od_module):
        """Load OD data from OD reader module (using registers list)"""
        try:
            self.od_registers = []
            for reg in od_module.registers:
                reg_copy = dict(reg)
                if "dataLength" in reg_copy:
                    reg_copy["data_length"] = reg_copy.pop("dataLength")
                self.od_registers.append(reg_copy)
            
            # Load PDO mappings if available
            if hasattr(od_module, 'pdo_mappings') and od_module.pdo_mappings:
                self.pdo_mappings = od_module.pdo_mappings
                self.build_cob_id_mapping()
                self.build_pdo_variables_table()
                self.logger.info(f"Loaded PDO mappings: {len(self.pdo_mappings.get('rpdos', []))} RPDOs, {len(self.pdo_mappings.get('tpdos', []))} TPDOs")
            
            self.logger.info(f"Loaded {len(self.od_registers)} OD registers for message interpretation")
        except Exception as e:
            self.logger.error(f"Error loading OD data: {e}")
    
    def build_cob_id_mapping(self):
        """Build mapping from COB-ID to PDO information for quick lookup"""
        self.cob_id_to_pdo = {}
        
        # Process RPDOs
        for rpdo in self.pdo_mappings.get('rpdos', []):
            if rpdo['enabled'] and rpdo['mapped_variables']:
                cob_id = rpdo['cob_id_clean']
                self.cob_id_to_pdo[cob_id] = {
                    'type': 'RPDO',
                    'pdo_info': rpdo
                }
        
        # Process TPDOs
        for tpdo in self.pdo_mappings.get('tpdos', []):
            if tpdo['enabled'] and tpdo['mapped_variables']:
                cob_id = tpdo['cob_id_clean']
                self.cob_id_to_pdo[cob_id] = {
                    'type': 'TPDO',
                    'pdo_info': tpdo
                }
        
        self.logger.info(f"Built COB-ID mapping for {len(self.cob_id_to_pdo)} enabled PDOs")
    
    def build_pdo_variables_table(self):
        """Build the PDO variables table with manufacturer registers only"""
        self.pdo_variables_table.rows.clear()
        self.pdo_variables = {}
        
        # Get variable names from OD registers (only manufacturer category)
        manufacturer_vars = {}
        for reg in self.od_registers:
            if reg.get('category') == 'Manufacturer':
                manufacturer_vars[reg['index']] = reg.get('name', 'Unknown')
        
        # Add only manufacturer variables that are mapped in PDOs
        for cob_id, pdo_info in self.cob_id_to_pdo.items():
            pdo_data = pdo_info['pdo_info']
            pdo_type = pdo_info['type']
            
            for var in pdo_data['mapped_variables']:
                var_index = var['index']
                
                # Only include manufacturer variables (0x2000-0x5FFF range)
                if var_index in manufacturer_vars:
                    var_name = manufacturer_vars[var_index]
                    
                    # Initialize variable value
                    self.pdo_variables[var_index] = {
                        'value': 'No data',
                        'cob_id': f"0x{cob_id:03X}",
                        'type': pdo_type,
                        'last_update': 'Never',
                        'bits': var['bit_length'],
                        'name': var_name,
                        'pdo_bit_offset': 0  # Will be calculated
                    }
                    
                    # Add row to table
                    new_row = ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(var_index, size=11)),
                            ft.DataCell(ft.Text(var_name[:20], size=11)),  # Truncate long names
                            ft.DataCell(ft.Text('No data', size=11)),
                            ft.DataCell(ft.Text(f"0x{cob_id:03X}", size=11)),
                            ft.DataCell(ft.Text('Never', size=11))
                        ]
                    )
                    self.pdo_variables_table.rows.append(new_row)
        
        # Update statistics
        self.stats_controls["pdo_count"].value = f"PDO Variables: {len(self.pdo_variables)}"
        self.page.update()
    
    def process_pdo_message(self, message: CANMessage):
        """Process PDO messages and extract variable values"""
        try:
            cob_id = message.cob_id

            # Si selected_node_id es 0, no filtrar por nodo
            if self.selected_node_id != 0:
                # El último dígito hexadecimal del COB-ID es el node-id
                node_id_from_cobid = cob_id & 0xF
                if node_id_from_cobid != self.selected_node_id:
                    return  # No procesar si no coincide el node-id

                # Normalizar el COB-ID quitando el node-id (último nibble)
                normalized_cob_id = cob_id & 0xFFF0
            else:
                normalized_cob_id = cob_id

            # Buscar el PDO usando el COB-ID normalizado
            # print(f"DEBUG: Processing PDO message with COB-ID: {cob_id:03X}, normalized: {normalized_cob_id:03X}")

            if normalized_cob_id not in self.cob_id_to_pdo:
                return

            pdo_info = self.cob_id_to_pdo[normalized_cob_id]
            pdo_data = pdo_info['pdo_info']
            
            # Extract values for each mapped variable
            bit_offset = 0
            for var in pdo_data['mapped_variables']:
                var_index = var['index']
                bit_length = var['bit_length']
                
                # Only process manufacturer variables
                if var_index not in self.pdo_variables:
                    bit_offset += bit_length
                    continue
                
                # Calculate byte positions
                byte_start = bit_offset // 8
                byte_end = (bit_offset + bit_length - 1) // 8
                
                if byte_end < len(message.data):
                    # Extract value based on bit length
                    if bit_length <= 8:
                        value = message.data[byte_start]
                        if bit_length < 8:
                            # Handle partial byte
                            bit_pos = bit_offset % 8
                            mask = ((1 << bit_length) - 1) << bit_pos
                            value = (value & mask) >> bit_pos
                    elif bit_length <= 16:
                        if byte_start + 1 < len(message.data):
                            value = message.data[byte_start] | (message.data[byte_start + 1] << 8)
                        else:
                            value = message.data[byte_start]
                    elif bit_length <= 32:
                        value = 0
                        for i in range(min(4, len(message.data) - byte_start)):
                            value |= message.data[byte_start + i] << (i * 8)
                    else:
                        # For larger values, show as hex string
                        hex_bytes = message.data[byte_start:byte_end + 1]
                        value = " ".join([f"{b:02X}" for b in hex_bytes])
                    
                    # Update variable value
                    self.pdo_variables[var_index]['value'] = str(value)
                    self.pdo_variables[var_index]['last_update'] = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
                
                bit_offset += bit_length
            
            # Update PDO table display
            self.update_pdo_variables_table()
            
        except Exception as e:
            self.logger.error(f"Error processing PDO message: {e}")
    
    def update_pdo_variables_table(self):
        """Update PDO variables table with current values"""
        try:
            for i, row in enumerate(self.pdo_variables_table.rows):
                if i < len(self.pdo_variables_table.rows):
                    # Get variable index from first cell
                    var_index = row.cells[0].content.value
                    if var_index in self.pdo_variables:
                        var_data = self.pdo_variables[var_index]
                        # Update value and timestamp cells
                        row.cells[2].content.value = str(var_data['value'])
                        row.cells[4].content.value = var_data['last_update'][:8]  # Show only time part
            
            # Don't update page here to avoid performance issues
        except Exception as e:
            self.logger.error(f"Error updating PDO variables table: {e}")
    
    def interpret_message_with_od(self, message: CANMessage) -> str:
        """Interpret CAN message using OD data if available"""
        try:
            if not self.od_registers:
                return message.message_type
            
            # Check if it's a PDO message
            if message.cob_id in self.cob_id_to_pdo:
                pdo_info = self.cob_id_to_pdo[message.cob_id]
                return f"{pdo_info['type']} (Variables)"
            
            # For SDO messages, try to find matching OD entry
            if message.message_type in ["SDO_REQUEST", "SDO_RESPONSE"] and len(message.data) >= 4:
                # Extract index from SDO message
                index_from_msg = f"0x{message.data[2]:02X}{message.data[1]:02X}"
                
                # Find matching OD entry
                for reg in self.od_registers:
                    if reg.get("index", "").upper() == index_from_msg.upper():
                        return f"{message.message_type} ({reg.get('name', 'Unknown')})"
            
            return message.message_type
            
        except Exception as e:
            self.logger.debug(f"Error interpreting message with OD: {e}")
            return message.message_type
    
    def on_message_received(self, message: CANMessage):
        """Callback for received CAN messages"""
        try:
            self.message_list.append(message)
            self.message_count += 1
            self.messages_since_last_update += 1

            # Process PDO messages if type starts with 'PDO', 'RPDO', or 'TPDO'
            if (
                isinstance(message.message_type, str)
                and (
                    message.message_type.startswith("PDO")
                    or message.message_type.startswith("RPDO")
                    or message.message_type.startswith("TPDO")
                )
            ):
                self.process_pdo_message(message)

            # Keep only last 1000 messages
            if len(self.message_list) > 1000:
                self.message_list.pop(0)

            # Add to table if it matches filter
            if self.filter_node_id is None or message.node_id == self.filter_node_id:
                # Format time
                time_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]

                # Format data as hex string
                data_str = " ".join([f"{b:02X}" for b in message.data])

                # Interpret message type using OD data if available
                interpreted_type = self.interpret_message_with_od(message)

                # Create new row
                new_row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(time_str)),
                        ft.DataCell(ft.Text(f"0x{message.cob_id:03X}")),
                        ft.DataCell(ft.Text(str(message.node_id))),
                        ft.DataCell(ft.Text(interpreted_type)),
                        ft.DataCell(ft.Text(data_str)),
                        ft.DataCell(ft.Text(str(message.length)))
                    ]
                )

                # Add to beginning of table (newest first)
                self.message_table.rows.insert(0, new_row)

                # Keep only last 100 rows in table for performance
                if len(self.message_table.rows) > 100:
                    self.message_table.rows.pop()

                # Update UI periodically (not every message for performance)
                if self.messages_since_last_update >= 10:
                    self.page.update()
                    self.messages_since_last_update = 0

        except Exception as ex:
            self.logger.error(f"Error processing received message: {ex}")
            self.error_count += 1
    
    def rebuild_message_table(self):
        """Rebuild message table with current filter"""
        self.message_table.rows.clear()
        
        filtered_messages = self.message_list
        if self.filter_node_id is not None:
            filtered_messages = [msg for msg in self.message_list if msg.node_id == self.filter_node_id]
        
        # Add last 100 messages to table (newest first)
        for message in reversed(filtered_messages[-100:]):
            time_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
            data_str = " ".join([f"{b:02X}" for b in message.data])
            
            # Interpret message type using OD data if available
            interpreted_type = self.interpret_message_with_od(message)
            
            new_row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(time_str)),
                    ft.DataCell(ft.Text(f"0x{message.cob_id:03X}")),
                    ft.DataCell(ft.Text(str(message.node_id))),
                    ft.DataCell(ft.Text(interpreted_type)),
                    ft.DataCell(ft.Text(data_str)),
                    ft.DataCell(ft.Text(str(message.length)))
                ]
            )
            
            self.message_table.rows.append(new_row)
        
        self.page.update()
    
    def start_stats_update(self):
        """Start statistics update thread"""
        def update_stats():
            while self.is_monitoring:
                self.update_statistics()
                time.sleep(1)  # Update every second
        
        stats_thread = threading.Thread(target=update_stats)
        stats_thread.daemon = True
        stats_thread.start()
    
    def update_statistics(self):
        """Update statistics display"""
        try:
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time
            
            if time_elapsed >= 1.0:  # Update rate every second
                rate = self.messages_since_last_update / time_elapsed
                self.stats_controls["rate"].value = f"Rate: {rate:.1f} msg/s"
                self.last_update_time = current_time
                self.messages_since_last_update = 0
            
            self.stats_controls["msg_count"].value = f"Messages: {self.message_count}"
            self.stats_controls["error_count"].value = f"Errors: {self.error_count}"
            
            # Update interface status
            if self.interface_manager.is_monitoring():
                self.stats_controls["interface_status"].value = "Status: Monitoring"
                self.stats_controls["interface_status"].color = ft.Colors.GREEN
            elif self.interface_manager.is_connected():
                self.stats_controls["interface_status"].value = "Status: Connected"
                self.stats_controls["interface_status"].color = ft.Colors.BLUE
            else:
                self.stats_controls["interface_status"].value = "Status: Disconnected"
                self.stats_controls["interface_status"].color = ft.Colors.RED
                
            self.page.update()
                
        except Exception as ex:
            self.logger.error(f"Error updating statistics: {ex}")
    
    def update_connection_status(self, connected: bool):
        """Update connection status display (called from interface manager)"""
        print(f"DEBUG: Monitor module - received connection status callback: {connected}")
        if connected:
            self.stats_controls["interface_status"].value = "Status: Connected"
            self.stats_controls["interface_status"].color = ft.Colors.BLUE
        else:
            self.stats_controls["interface_status"].value = "Status: Disconnected"
            self.stats_controls["interface_status"].color = ft.Colors.RED
            # Stop monitoring if disconnected
            if self.is_monitoring:
                self.stop_monitoring(None)
        
        self.update_button_states()
        self.page.update()
    
    def update_button_states(self):
        """Update button enabled/disabled states"""
        print(f"DEBUG: Monitor module - updating button states. Connected: {self.interface_manager.is_connected() if self.interface_manager else False}, Monitoring: {self.is_monitoring}")
        if self.control_buttons and len(self.control_buttons.controls) >= 2:
            start_button = self.control_buttons.controls[0]
            stop_button = self.control_buttons.controls[1]
            
            is_connected = self.interface_manager.is_connected() if self.interface_manager else False
            start_button.disabled = not is_connected or self.is_monitoring
            stop_button.disabled = not self.is_monitoring
            
            self.page.update()
    
    def set_interface_manager(self, interface_manager: InterfaceManager):
        """Set the interface manager from external module"""
        self.interface_manager = interface_manager
        self.update_button_states()
