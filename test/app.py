#!/usr/bin/env python3
"""
CAN Message Analyzer Application

PURPOSE:
Main application that integrates the message processor with the GUI interface.
Provides a complete solution for CAN message monitoring and analysis with
real-time visualization of network activity.

KEY FEATURES:
- Integrated GUI and message processing
- Real-time COB-ID monitoring
- Network statistics and analysis
- Graceful startup and shutdown
- Error handling and recovery
"""

import sys
import time
import threading
import signal
from typing import Optional

# Import our modules
try:
    from usb_serial_interface import UltraHighSpeedCANInterface
    from message_processor import CANMessageProcessor
    from can_gui import CANStackGUI
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required modules are in the same directory:")
    print("  - usb_serial_interface.py")
    print("  - message_processor.py") 
    print("  - can_message.py")
    print("  - can_message_stack.py")
    print("  - can_gui.py")
    sys.exit(1)

class CANAnalyzerApp:
    """
    Main application class that coordinates all components
    """
    
    def __init__(self, com_port: str = "COM7", baudrate: int = 2000000):
        self.com_port = com_port
        self.baudrate = baudrate
        
        # Components
        self.interface: Optional[UltraHighSpeedCANInterface] = None
        self.processor: Optional[CANMessageProcessor] = None
        self.gui: Optional[CANStackGUI] = None
        
        # Control flags
        self.running = False
        self.cleanup_started = False
        
        # Configuration
        self.batch_size = 25
        self.processing_interval = 0.05
        self.debug_enabled = False
        
        print(f"🚀 CAN Analyzer Application")
        print(f"📡 Interface: {com_port} @ {baudrate:,} baud")
        print(f"🖥️  GUI: tkinter-based real-time monitor")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        if self.cleanup_started:
            print(f"\n⚠️  Cleanup already in progress...")
            return
        
        print(f"\n🛑 Received signal {signum} - shutting down gracefully...")
        self.shutdown()
    
    def initialize_components(self) -> bool:
        """Initialize all application components"""
        try:
            print(f"\n🔧 Initializing components...")
            
            # 1. Initialize USB Serial Interface
            print(f"📡 Creating USB serial interface...")
            self.interface = UltraHighSpeedCANInterface(
                com_port=self.com_port,
                baudrate=self.baudrate,
                debug=self.debug_enabled
            )
            
            # 2. Initialize Message Processor
            print(f"⚙️  Creating message processor...")
            self.processor = CANMessageProcessor(
                serial_interface=self.interface,
                batch_size=self.batch_size,
                processing_interval=self.processing_interval,
                debug=self.debug_enabled
            )
            
            # 3. Initialize GUI
            print(f"🖥️  Creating GUI...")
            self.gui = CANStackGUI(message_processor=self.processor)
            
            print(f"✅ All components initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            return False
    
    def start_system(self) -> bool:
        """Start all system components"""
        try:
            print(f"\n🚀 Starting system components...")
            
            # 1. Connect interface
            print(f"📡 Connecting to {self.com_port}...")
            if not self.interface.connect():
                print(f"❌ Failed to connect to interface")
                return False
            
            # 2. Start interface monitoring
            print(f"👀 Starting interface monitoring...")
            if not self.interface.start_monitoring():
                print(f"❌ Failed to start interface monitoring")
                return False
            
            # Give interface time to start receiving data
            print(f"⏳ Waiting for interface to stabilize...")
            time.sleep(2.0)
            
            # 3. Start message processor
            print(f"⚙️  Starting message processor...")
            if not self.processor.start_processing():
                print(f"❌ Failed to start message processor")
                return False
            
            # 4. Start GUI (this will run in main thread)
            print(f"🖥️  Starting GUI...")
            self.gui.set_message_processor(self.processor)
            
            self.running = True
            print(f"✅ System started successfully!")
            print(f"\n🔥 CAN ANALYZER ACTIVE")
            print(f"📊 Real-time COB-ID monitoring with GUI")
            print(f"💡 Close the GUI window to stop the application")
            print(f"=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting system: {e}")
            return False
    
    def run_application(self):
        """Run the main application"""
        try:
            # Start GUI (blocks until window is closed)
            self.gui.run()
            
        except Exception as e:
            print(f"❌ Error running application: {e}")
        
        finally:
            # GUI closed, shutdown system
            print(f"\n🖥️  GUI closed, shutting down system...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all components gracefully"""
        if self.cleanup_started:
            return
        
        self.cleanup_started = True
        self.running = False
        
        print(f"\n🛑 Shutting down CAN Analyzer...")
        
        try:
            # Stop GUI updates
            if self.gui:
                print(f"🖥️  Stopping GUI updates...")
                self.gui.stop_updates()
            
            # Stop message processor
            if self.processor:
                print(f"⚙️  Stopping message processor...")
                self.processor.stop_processing()
            
            # Disconnect interface
            if self.interface:
                print(f"📡 Disconnecting interface...")
                self.interface.disconnect()
            
            print(f"✅ Shutdown completed successfully")
            
        except Exception as e:
            print(f"⚠️  Error during shutdown: {e}")
    
    def print_startup_info(self):
        """Print application startup information"""
        print(f"\n" + "=" * 60)
        print(f"🔄 CAN MESSAGE ANALYZER - INTEGRATED APPLICATION")
        print(f"=" * 60)
        print(f"📡 Serial Interface:")
        print(f"   • Port: {self.com_port}")
        print(f"   • Baudrate: {self.baudrate:,} baud")
        print(f"   • Debug: {'ON' if self.debug_enabled else 'OFF'}")
        print(f"")
        print(f"⚙️  Message Processor:")
        print(f"   • Batch size: {self.batch_size} messages")
        print(f"   • Processing interval: {self.processing_interval}s")
        print(f"   • COB-ID organized stack: ✅")
        print(f"   • Modular architecture: ✅")
        print(f"")
        print(f"🖥️  GUI Features:")
        print(f"   • Real-time COB-ID list")
        print(f"   • Network statistics")
        print(f"   • Message type breakdown")
        print(f"   • Activity indicators")
        print(f"=" * 60)


def main():
    """Main entry point"""
    # Configuration
    COM_PORT = "COM7"  # Change this to your COM port
    BAUDRATE = 2000000  # 2M baud
    
    # Create application
    app = CANAnalyzerApp(com_port=COM_PORT, baudrate=BAUDRATE)
    
    # Print startup information
    app.print_startup_info()
    
    # Setup signal handlers
    app.setup_signal_handlers()
    
    try:
        # Initialize all components
        if not app.initialize_components():
            print(f"❌ Failed to initialize application")
            return 1
        
        # Start system
        if not app.start_system():
            print(f"❌ Failed to start system")
            return 1
        
        # Run application (blocks until GUI is closed)
        app.run_application()
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⌨️  Keyboard interrupt received")
        app.shutdown()
        return 0
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        app.shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(main())
