from typing import Any
from datetime import datetime

class TrackedVariable:
    def __init__(self, index: str, sub_index: str, name: str, category: str, data_type: str = "Unknown"):
        self.index = index
        self.sub_index = sub_index
        self.name = name
        self.category = category
        self.data_type = data_type
        self.current_value = "N/A"
        self.last_update = None
        self.update_count = 0
        
    def update_value(self, value: Any):
        """Update variable value from CAN message"""
        self.current_value = str(value)
        self.last_update = datetime.now()
        self.update_count += 1
