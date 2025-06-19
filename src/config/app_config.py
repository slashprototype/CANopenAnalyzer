import json
import os
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class CANConfig:
    interface: str = "socketcan"  # "socketcan" or "usb_serial"
    channel: str = "can0"
    bitrate: int = 125000
    timeout: float = 1.0
    # USB Serial specific settings
    com_port: str = "COM1"
    serial_baudrate: int = 115200

@dataclass
class UIConfig:
    theme: str = "light"
    auto_refresh_rate: int = 100  # ms
    max_log_entries: int = 1000
    graph_update_rate: int = 500  # ms

@dataclass
class NetworkConfig:
    node_id: int = 1
    heartbeat_period: int = 1000  # ms
    sdo_timeout: float = 5.0
    emergency_timeout: float = 2.0

class AppConfig:
    def __init__(self, config_file: str = "config/app_config.json"):
        self.config_file = config_file
        self.can_config = CANConfig()
        self.ui_config = UIConfig()
        self.network_config = NetworkConfig()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                if 'can' in data:
                    self.can_config = CANConfig(**data['can'])
                if 'ui' in data:
                    self.ui_config = UIConfig(**data['ui'])
                if 'network' in data:
                    self.network_config = NetworkConfig(**data['network'])
                    
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        data = {
            'can': asdict(self.can_config),
            'ui': asdict(self.ui_config),
            'network': asdict(self.network_config)
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
