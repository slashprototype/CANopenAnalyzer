"""
Interfaces module for different CAN communication methods.
"""

from .base_interface import BaseCANInterface, CANMessage
from .usb_serial_interface import USBSerialCANInterface
from .interface_factory import CANInterfaceFactory
from .interface_manager import InterfaceManager

__all__ = ['BaseCANInterface', 'CANMessage', 'USBSerialCANInterface', 'CANInterfaceFactory', 'InterfaceManager']
