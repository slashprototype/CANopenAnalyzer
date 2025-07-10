#!/usr/bin/env python3
"""
CAN Message Stack Module

PURPOSE:
This module provides a sophisticated message stack that organizes CAN messages by COB-ID.
It maintains the latest message for each COB-ID, automatically updating when newer messages
arrive. This creates a real-time snapshot of the CANopen network state.

KEY FEATURES:
- Organized storage by COB-ID (no duplicates per COB-ID)
- Automatic message updating (latest message per COB-ID)
- Thread-safe operations
- Message aging and expiration
- Statistics and monitoring
- Query capabilities by COB-ID, node ID, and message type
- Export capabilities for analysis

The stack serves as a live view of the network state, always containing the most recent
message from each active COB-ID.
"""

import threading
import time
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime
from can_message import CANMessage, CANMessageType

class CANMessageStack:
    """
    Thread-safe stack for organizing CAN messages by COB-ID
    Automatically updates with latest messages, no duplicates per COB-ID
    """
    
    def __init__(self, max_age_seconds: float = 300.0, debug: bool = False):
        """
        Initialize message stack
        
        Args:
            max_age_seconds: Maximum age for messages before they're considered stale
            debug: Enable debug output
        """
        self.max_age_seconds = max_age_seconds
        self._debug_enabled = debug
        
        # Main storage: COB-ID -> Latest CANMessage
        self._messages: Dict[int, CANMessage] = {}
        
        # Secondary indexes for fast queries
        self._by_node_id: Dict[int, Set[int]] = defaultdict(set)  # node_id -> set of cob_ids
        self._by_msg_type: Dict[str, Set[int]] = defaultdict(set)  # msg_type -> set of cob_ids
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_messages_received': 0,
            'total_cobids_active': 0,
            'messages_updated': 0,
            'messages_added': 0,
            'messages_expired': 0,
            'last_update_time': 0.0,
            'start_time': time.time()
        }
    
    def update_message(self, message: CANMessage) -> bool:
        """Update or add message to stack"""
        try:
            with self._lock:
                cob_id = message.cob_id
                is_new_cobid = cob_id not in self._messages
                
                # Store/update message
                old_message = self._messages.get(cob_id)
                self._messages[cob_id] = message
                
                # Update secondary indexes
                self._update_indexes(message, old_message)
                
                # Update statistics
                self._stats['total_messages_received'] += 1
                self._stats['last_update_time'] = time.time()
                
                if is_new_cobid:
                    self._stats['messages_added'] += 1
                    self._stats['total_cobids_active'] = len(self._messages)
                else:
                    self._stats['messages_updated'] += 1
                
                return True
                
        except Exception as e:
            return False
    
    def update_from_tuple(self, message_tuple: tuple) -> bool:
        """
        Update message from tuple format
        
        Args:
            message_tuple: (timestamp, cob_id, data, msg_type, msg_index)
            
        Returns:
            True if successful
        """
        try:
            message = CANMessage.from_tuple(message_tuple)
            return self.update_message(message)
        except Exception as e:
            self._debug_print(f"Error creating message from tuple: {e}")
            return False
    
    def get_message(self, cob_id: int) -> Optional[CANMessage]:
        """Get latest message for specific COB-ID"""
        with self._lock:
            return self._messages.get(cob_id)
    
    def get_messages_by_node(self, node_id: int) -> List[CANMessage]:
        """Get all latest messages from specific node"""
        with self._lock:
            cob_ids = self._by_node_id.get(node_id, set())
            return [self._messages[cob_id] for cob_id in cob_ids if cob_id in self._messages]
    
    def get_messages_by_type(self, msg_type: str) -> List[CANMessage]:
        """Get all latest messages of specific type"""
        with self._lock:
            cob_ids = self._by_msg_type.get(msg_type, set())
            return [self._messages[cob_id] for cob_id in cob_ids if cob_id in self._messages]
    
    def get_all_messages(self) -> List[CANMessage]:
        """Get all latest messages"""
        with self._lock:
            return list(self._messages.values())
    
    def get_active_cobids(self) -> List[int]:
        """Get list of all active COB-IDs"""
        with self._lock:
            return list(self._messages.keys())
    
    def get_active_nodes(self) -> List[int]:
        """Get list of all active node IDs"""
        with self._lock:
            return list(self._by_node_id.keys())
    
    def get_message_types(self) -> List[str]:
        """Get list of all active message types"""
        with self._lock:
            return list(self._by_msg_type.keys())
    
    def is_cobid_active(self, cob_id: int) -> bool:
        """Check if COB-ID has recent activity"""
        message = self.get_message(cob_id)
        if not message:
            return False
        return message.age_seconds <= self.max_age_seconds
    
    def is_node_active(self, node_id: int) -> bool:
        """Check if node has recent activity"""
        messages = self.get_messages_by_node(node_id)
        return any(msg.age_seconds <= self.max_age_seconds for msg in messages)
    
    def _update_indexes(self, new_message: CANMessage, old_message: Optional[CANMessage]):
        """Update secondary indexes"""
        cob_id = new_message.cob_id
        
        # Remove old indexes if message changed
        if old_message:
            if old_message.node_id is not None:
                self._by_node_id[old_message.node_id].discard(cob_id)
                if not self._by_node_id[old_message.node_id]:
                    del self._by_node_id[old_message.node_id]
            
            self._by_msg_type[old_message.msg_type].discard(cob_id)
            if not self._by_msg_type[old_message.msg_type]:
                del self._by_msg_type[old_message.msg_type]
        
        # Add new indexes
        if new_message.node_id is not None:
            self._by_node_id[new_message.node_id].add(cob_id)
        
        self._by_msg_type[new_message.msg_type].add(cob_id)
    
    def get_statistics(self) -> Dict:
        """Get stack statistics"""
        with self._lock:
            uptime = time.time() - self._stats['start_time']
            avg_rate = self._stats['total_messages_received'] / uptime if uptime > 0 else 0
            
            stats = self._stats.copy()
            stats.update({
                'uptime_seconds': uptime,
                'average_message_rate': avg_rate,
                'active_cobids': len(self._messages),
                'active_nodes': len(self._by_node_id),
                'active_message_types': len(self._by_msg_type)
            })
            return stats
    
    def get_network_summary(self) -> Dict:
        """Get comprehensive network summary"""
        with self._lock:
            summary = {
                'total_active_cobids': len(self._messages),
                'total_active_nodes': len(self._by_node_id),
                'message_types': {},
                'nodes': {},
                'cobids': {}
            }
            
            # Count by message type
            for msg_type, cob_ids in self._by_msg_type.items():
                summary['message_types'][msg_type] = len(cob_ids)
            
            # Node information
            for node_id, cob_ids in self._by_node_id.items():
                node_messages = [self._messages[cob_id] for cob_id in cob_ids]
                summary['nodes'][node_id] = {
                    'cobids': list(cob_ids),
                    'message_count': len(node_messages),
                    'message_types': list(set(msg.msg_type for msg in node_messages)),
                    'last_activity': min(msg.age_seconds for msg in node_messages)
                }
            
            # COB-ID information
            for cob_id, message in self._messages.items():
                summary['cobids'][f"0x{cob_id:03X}"] = {
                    'node_id': message.node_id,
                    'msg_type': message.msg_type,
                    'data_length': len(message.data),
                    'age_seconds': message.age_seconds
                }
            
            return summary
    
    def clear(self):
        """Clear all messages from stack"""
        with self._lock:
            self._messages.clear()
            self._by_node_id.clear()
            self._by_msg_type.clear()
            self._stats['total_cobids_active'] = 0
            self._debug_print("Stack cleared")
    
    def _debug_print(self, message: str, verbose: bool = False):
        """Print debug message if debugging is enabled"""
        if self._debug_enabled and (not verbose):
            print(f"[DEBUG-STACK] {message}")
    
    def enable_debug(self, enabled: bool = True):
        """Enable or disable debug output"""
        self._debug_enabled = enabled
        if enabled:
            self._debug_print("Debug enabled for message stack")
    
    def __len__(self) -> int:
        """Return number of active COB-IDs"""
        return len(self._messages)
    
    def __contains__(self, cob_id: int) -> bool:
        """Check if COB-ID exists in stack"""
        return cob_id in self._messages
    
    def __str__(self) -> str:
        """String representation of stack"""
        with self._lock:
            return (f"CANMessageStack: {len(self._messages)} COB-IDs, "
                    f"{len(self._by_node_id)} nodes")

    def clear(self):
        """Clear all messages from stack"""
        with self._lock:
            self._messages.clear()
            self._by_node_id.clear()
            self._by_msg_type.clear()
            self._stats['total_cobids_active'] = 0
            self._debug_print("Stack cleared")
    
    def _debug_print(self, message: str, verbose: bool = False):
        """Print debug message if debugging is enabled"""
        if self._debug_enabled and (not verbose):
            print(f"[DEBUG-STACK] {message}")
    
    def enable_debug(self, enabled: bool = True):
        """Enable or disable debug output"""
        self._debug_enabled = enabled
        if enabled:
            self._debug_print("Debug enabled for message stack")
    
    def __len__(self) -> int:
        """Return number of active COB-IDs"""
        return len(self._messages)
    
    def __contains__(self, cob_id: int) -> bool:
        """Check if COB-ID exists in stack"""
        return cob_id in self._messages
    
    def __str__(self) -> str:
        """String representation of stack"""
        with self._lock:
            return (f"CANMessageStack: {len(self._messages)} COB-IDs, "
                    f"{len(self._by_node_id)} nodes, "
                    f"{self._stats['total_messages_received']} total messages")
