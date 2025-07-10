#!/usr/bin/env python3
"""
Simple CAN Message Stack GUI Module

PURPOSE:
Provides a simple tkinter-based GUI to display COB-IDs being added and updated
in the CAN message stack. Shows real-time network activity in an easy-to-read format.

KEY FEATURES:
- Real-time COB-ID list display with high precision timestamps
- Message type and node information
- Activity indicators and timestamps with milliseconds/microseconds
- Simple and clean interface
- Integration with CANMessageProcessor
- High-frequency updates (100ms) for fast CAN data
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime

class CANStackGUI:
    """
    Simple GUI for displaying CAN message stack activity
    """
    
    def __init__(self, message_processor=None):
        self.message_processor = message_processor
        self.root = tk.Tk()
        self.running = False
        self.update_thread = None
        
        # GUI components
        self.cobid_tree = None
        self.status_label = None
        self.stats_text = None
        
        # Update control - High frequency for fast CAN data
        self.update_interval = 0.1  # Update every 100ms for high-speed data
        self.last_cobid_count = 0
        
        self._setup_gui()
    
    def _setup_gui(self):
        """Setup the GUI components"""
        self.root.title("CAN Message Stack Monitor - High Speed")
        self.root.geometry("900x600")  # Slightly wider for timestamp
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title and status
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="🔄 CAN Message Stack - Active COB-IDs", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        self.status_label = ttk.Label(title_frame, text="Status: Disconnected", 
                                     foreground="red")
        self.status_label.grid(row=0, column=1, sticky=tk.E)
        title_frame.columnconfigure(1, weight=1)
        
        # COB-ID Tree view
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Create treeview with columns - Updated for high precision timestamp
        columns = ("COB-ID", "Node", "Type", "Data Length", "Timestamp", "Age (ms)")
        self.cobid_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.cobid_tree.heading("COB-ID", text="COB-ID")
        self.cobid_tree.heading("Node", text="Node ID")
        self.cobid_tree.heading("Type", text="Message Type")
        self.cobid_tree.heading("Data Length", text="Data Len")
        self.cobid_tree.heading("Timestamp", text="Timestamp (HH:MM:SS.mmm)")
        self.cobid_tree.heading("Age (ms)", text="Age (ms)")
        
        # Column widths - Adjusted for timestamp with milliseconds
        self.cobid_tree.column("COB-ID", width=80)
        self.cobid_tree.column("Node", width=60)
        self.cobid_tree.column("Type", width=100)
        self.cobid_tree.column("Data Length", width=80)
        self.cobid_tree.column("Timestamp", width=140)  # Wider for milliseconds
        self.cobid_tree.column("Age (ms)", width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.cobid_tree.yview)
        self.cobid_tree.configure(yscrollcommand=scrollbar.set)
        
        self.cobid_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Statistics panel
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="5")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        stats_frame.columnconfigure(0, weight=1)
        
        self.stats_text = tk.Text(stats_frame, height=6, width=80)
        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Clear Display", command=self._clear_display).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="Refresh Now", command=self._refresh_display).grid(row=0, column=1, padx=(0, 10))
        
        # Initial display
        self._display_no_data()
    
    def set_message_processor(self, processor):
        """Set the message processor for data updates"""
        self.message_processor = processor
        if processor:
            self.status_label.config(text="Status: Connected", foreground="green")
        else:
            self.status_label.config(text="Status: Disconnected", foreground="red")
    
    def start_updates(self):
        """Start the GUI update thread"""
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        print("🖥️  GUI update thread started")
    
    def stop_updates(self):
        """Stop the GUI updates"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=2.0)
        print("🖥️  GUI updates stopped")
    
    def _update_loop(self):
        """Main update loop for GUI"""
        try:
            while self.running:
                if self.message_processor:
                    self._update_display()
                time.sleep(self.update_interval)
        except Exception as e:
            print(f"❌ Error in GUI update loop: {e}")
    
    def _update_display(self):
        """Update the display with current stack data"""
        try:
            if not self.message_processor or not self.message_processor.message_stack:
                return
            
            # Get all messages from stack
            all_messages = self.message_processor.message_stack.get_all_messages()
            
            # Schedule GUI update in main thread
            self.root.after(0, self._update_cobid_list, all_messages)
            self.root.after(0, self._update_statistics)
            
        except Exception as e:
            print(f"❌ Error updating display: {e}")
    
    def _update_cobid_list(self, messages):
        """Update the COB-ID list in the GUI with high precision timestamps"""
        try:
            # Clear existing items
            for item in self.cobid_tree.get_children():
                self.cobid_tree.delete(item)
            
            if not messages:
                self._display_no_data()
                return
            
            # Sort messages by COB-ID
            sorted_messages = sorted(messages, key=lambda msg: msg.cob_id)
            
            # Add messages to tree
            for msg in sorted_messages:
                cob_id_str = f"0x{msg.cob_id:03X}"
                node_str = str(msg.node_id) if msg.node_id is not None else "N/A"
                data_len = len(msg.data)
                
                # High precision timestamp with milliseconds
                timestamp_dt = datetime.fromtimestamp(msg.timestamp)
                milliseconds = int((msg.timestamp % 1) * 1000)
                timestamp_str = f"{timestamp_dt.strftime('%H:%M:%S')}.{milliseconds:03d}"
                
                # Age in milliseconds for better precision with fast data
                age_ms = f"{msg.age_seconds * 1000:.1f}"
                
                # Color coding based on age (in milliseconds for fast data)
                age_ms_value = msg.age_seconds * 1000
                tags = []
                if age_ms_value < 1000:  # Less than 1000ms
                    tags.append("fresh")
                elif age_ms_value < 2000:  # Less than 2000ms
                    tags.append("recent")
                else:
                    tags.append("old")
                
                self.cobid_tree.insert("", "end", values=(
                    cob_id_str, node_str, msg.msg_type, data_len, timestamp_str, age_ms
                ), tags=tags)
            
            # Configure tag colors for high-speed data
            self.cobid_tree.tag_configure("fresh", background="#e8f5e8")    # Light green - very recent
            self.cobid_tree.tag_configure("recent", background="#fff3cd")   # Light yellow - recent
            self.cobid_tree.tag_configure("old", background="#f8d7da")      # Light red - old
            
        except Exception as e:
            print(f"❌ Error updating COB-ID list: {e}")
    
    def _update_statistics(self):
        """Update the statistics display with high-frequency update info"""
        try:
            if not self.message_processor:
                return
            
            # Get processor statistics
            proc_stats = self.message_processor.get_statistics()
            stack_stats = self.message_processor.get_message_stack_statistics()
            network_summary = self.message_processor.get_network_summary()
            
            # Create statistics text with update frequency info
            stats_text = []
            stats_text.append(f"📊 PROCESSING STATISTICS (Updated every 100ms):")
            stats_text.append(f"   • Messages/second: {proc_stats.get('messages_per_second', 0):,}")
            stats_text.append(f"   • Total processed: {proc_stats.get('total_processed', 0):,}")
            stats_text.append(f"   • Total batches: {proc_stats.get('total_batches', 0):,}")
            
            stats_text.append(f"\n🏠 NETWORK SUMMARY:")
            stats_text.append(f"   • Active COB-IDs: {network_summary.get('total_active_cobids', 0)}")
            stats_text.append(f"   • Active nodes: {network_summary.get('total_active_nodes', 0)}")
            
            # Message type breakdown
            msg_types = network_summary.get('message_types', {})
            if msg_types:
                type_summary = ", ".join([f"{t}:{c}" for t, c in msg_types.items()])
                stats_text.append(f"   • Message types: {type_summary}")
            
            # Add timestamp precision info
            stats_text.append(f"\n⏱️ TIMING INFO:")
            stats_text.append(f"   • GUI update rate: {self.update_interval*1000:.0f}ms")
            stats_text.append(f"   • Timestamp precision: milliseconds")
            stats_text.append(f"   • Age precision: milliseconds")
            
            # Update statistics text widget
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, "\n".join(stats_text))
            
        except Exception as e:
            print(f"❌ Error updating statistics: {e}")
    
    def _display_no_data(self):
        """Display message when no data is available"""
        # Clear tree
        for item in self.cobid_tree.get_children():
            self.cobid_tree.delete(item)
        
        # Add placeholder message with updated column format
        self.cobid_tree.insert("", "end", values=(
            "No Data", "---", "Waiting for messages...", "---", "---", "---"
        ))
        
        # Clear statistics
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, "📊 Waiting for high-speed CAN data...\n\n" +
                                     "Start the message processor to see network activity.\n" +
                                     "GUI updates every 100ms for real-time monitoring.")
    
    def _clear_display(self):
        """Clear the display"""
        for item in self.cobid_tree.get_children():
            self.cobid_tree.delete(item)
        self.stats_text.delete(1.0, tk.END)
        self._display_no_data()
    
    def _refresh_display(self):
        """Force refresh of display"""
        if self.message_processor:
            self._update_display()
    
    def _on_closing(self):
        """Handle window closing"""
        self.stop_updates()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the GUI main loop"""
        print("🖥️  Starting CAN Stack GUI...")
        self.start_updates()
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n⌨️  GUI interrupted")
        finally:
            self.stop_updates()
