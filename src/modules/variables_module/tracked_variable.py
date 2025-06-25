from typing import Any, Optional
from datetime import datetime

class TrackedVariable:
    def __init__(self, index: str, name: str, category: str, data_length: int):
        self.index = index
        self.name = name
        self.category = category
        self.data_length = data_length
        self.current_value = "N/A"
        self.last_update = None
        self.update_count = 0

    def update_value(self, value: Any):
        """Update variable value from CAN message"""
        self.current_value = str(value)
        self.last_update = datetime.now()
        self.update_count += 1

    def get_full_index(self) -> str:
        """Get full index as string"""
        return f"{self.index}"
    
    def __str__(self) -> str:
        return f"TrackedVariable({self.get_full_index()}: {self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __repr__(self) -> str:
        return self.__str__()
