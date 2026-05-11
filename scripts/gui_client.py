"""
QuantDinger Local Trade Executor - GUI Client

A graphical interface for managing the local trade executor with:
- WebSocket connection status monitoring
- API key and configuration management
- Real-time log viewing
- Trading signal monitoring
- One-click start/stop control

Usage:
    python gui_client.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import asyncio
import threading
import queue
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class LogHandler:
    """Thread-safe log handler that writes to both console and GUI."""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.log_queue = queue.Queue()
        
    def write(self, message):
        self.log_queue.put(message)
        
    def flush(self):
        pass
        
    def update(self):
        """Process all pending log messages."""
        while not self.log_queue.empty():
            try:
                message = self.log_queue.get_nowait()
                self.text_widget.configure(state='normal')
                self.text_widget.insert('end', message)
                self.text_widget.see('end')
                self.text_widget.configure(state='disabled')
            except queue.Empty:
                break


class QuantDingerGUI:
    """Main GUI application for QuantDinger Local Trade Executor."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("QuantDinger Local Trade Executor")
        self.root.geometry("1200x800")
        
        # State
        self.connected = False
        self.websocket = None
        self.executor_thread = None
        self.stop_event = threading.Event()
        self.message_queue = queue.Queue()
        
        # Configuration
        self.config_file = "gui_config.json"
        self.config = self.load_config()
        
        # Create UI
        self.create_widgets()
        self.load_config_to_ui()
        
        # Start log updater
        self.update_logs()
        
    def create_widgets(self):
        """Create all UI widgets."""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # ===== Configuration Section =====
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # API Key
        ttk.Label(config_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar(value=self.config.get('api_key', ''))
        api_key_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, width=50, show='*')
        api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Cloud URL
        ttk.Label(config_frame, text="Cloud URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.cloud_url_var = tk.StringVar(value=self.config.get('cloud_url', 'ws://localhost:8765/ws'))
        cloud_url_entry = ttk.Entry(config_frame, textvariable=self.cloud_url_var, width=50)
        cloud_url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Broker Type
        ttk.Label(config_frame, text="Broker:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.broker_var = tk.StringVar(value=self.config.get('broker', 'simulation'))
        broker_combo = ttk.Combobox(config_frame, textvariable=self.broker_var, 
                                     values=['simulation', 'mt5', 'ibkr'], state='readonly', width=20)
        broker_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save Config Button
        save_btn = ttk.Button(config_frame, text="Save Config", command=self.save_config_from_ui)
        save_btn.grid(row=2, column=2, padx=5, pady=5)
        
        # ===== Connection Status Section =====
        status_frame = ttk.LabelFrame(main_frame, text="Connection Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status indicator
        self.status_label = ttk.Label(status_frame, text="● Disconnected", foreground="red", font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # Signal count
        self.signal_count_label = ttk.Label(status_frame, text="Signals Received: 0")
        self.signal_count_label.grid(row=0, column=1, sticky=tk.W, padx=20)
        
        # Trade count
        self.trade_count_label = ttk.Label(status_frame, text="Trades Executed: 0")
        self.trade_count_label.grid(row=0, column=2, sticky=tk.W, padx=20)
        
        # Last signal time
        self.last_signal_label = ttk.Label(status_frame, text="Last Signal: N/A")
        self.last_signal_label.grid(row=0, column=3, sticky=tk.W, padx=20)
        
        # ===== Control Buttons =====
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_btn = ttk.Button(control_frame, text="▶ Start", command=self.start_executor, style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop", command=self.stop_executor, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        clear_log_btn = ttk.Button(control_frame, text="🗑 Clear Logs", command=self.clear_logs)
        clear_log_btn.pack(side=tk.LEFT, padx=5)
        
        export_log_btn = ttk.Button(control_frame, text="💾 Export Logs", command=self.export_logs)
        export_log_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== Signal Monitor Section =====
        signal_frame = ttk.LabelFrame(main_frame, text="Recent Signals", padding="10")
        signal_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(0, 5))
        signal_frame.columnconfigure(0, weight=1)
        signal_frame.rowconfigure(0, weight=1)
        
        # Signal listbox with scrollbar
        signal_scrollbar = ttk.Scrollbar(signal_frame)
        signal_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.signal_listbox = tk.Listbox(signal_frame, yscrollcommand=signal_scrollbar.set, height=15)
        self.signal_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        signal_scrollbar.config(command=self.signal_listbox.yview)
        
        # ===== Log Section =====
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text area with scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', 
                                                    font=('Consolas', 9), height=15,
                                                    yscrollcommand=log_scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.config(command=self.log_text.yview)
        
        # Setup custom log handler
        self.log_handler = LogHandler(self.log_text)
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
        return {}
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def load_config_to_ui(self):
        """Load configuration into UI fields."""
        if 'api_key' in self.config:
            self.api_key_var.set(self.config['api_key'])
        if 'cloud_url' in self.config:
            self.cloud_url_var.set(self.config['cloud_url'])
        if 'broker' in self.config:
            self.broker_var.set(self.config['broker'])
    
    def save_config_from_ui(self):
        """Save current UI configuration to file."""
        config = {
            'api_key': self.api_key_var.get(),
            'cloud_url': self.cloud_url_var.get(),
            'broker': self.broker_var.get(),
        }
        self.save_config(config)
        self.log_message("✓ Configuration saved")
        messagebox.showinfo("Success", "Configuration saved successfully!")
    
    def log_message(self, message: str):
        """Add a message to the log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}\n"
        self.log_handler.write(formatted_msg)
    
    def update_logs(self):
        """Periodically update log display."""
        self.log_handler.update()
        self.root.after(100, self.update_logs)
    
    def clear_logs(self):
        """Clear the log display."""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
        self.log_message("Logs cleared")
    
    def export_logs(self):
        """Export logs to a file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"quantdinger_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get('1.0', 'end'))
                messagebox.showinfo("Success", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {e}")
    
    def update_status(self, connected: bool):
        """Update connection status display."""
        self.connected = connected
        if connected:
            self.status_label.config(text="● Connected", foreground="green")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        else:
            self.status_label.config(text="● Disconnected", foreground="red")
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def add_signal_to_monitor(self, signal_data: Dict[str, Any]):
        """Add a signal to the monitor listbox."""
        timestamp = signal_data.get('timestamp', '')[:19]
        strategy = signal_data.get('strategy_name', 'N/A')
        symbol = signal_data.get('symbol', 'N/A')
        signal_type = signal_data.get('signal_type', 'N/A')
        
        entry = f"{timestamp} | {strategy} | {symbol} | {signal_type}"
        self.signal_listbox.insert('end', entry)
        self.signal_listbox.see('end')
        
        # Update last signal time
        self.last_signal_label.config(text=f"Last Signal: {timestamp}")
    
    def start_executor(self):
        """Start the trade executor in a background thread."""
        api_key = self.api_key_var.get().strip()
        cloud_url = self.cloud_url_var.get().strip()
        broker = self.broker_var.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter an API Key")
            return
        
        if not cloud_url:
            messagebox.showerror("Error", "Please enter a Cloud URL")
            return
        
        if not WEBSOCKETS_AVAILABLE:
            messagebox.showerror("Error", "websockets library not installed.\nInstall with: pip install websockets")
            return
        
        self.log_message(f"Starting executor: broker={broker}, url={cloud_url}")
        self.stop_event.clear()
        
        # Start executor in background thread
        self.executor_thread = threading.Thread(
            target=self.run_executor,
            args=(api_key, cloud_url, broker),
            daemon=True
        )
        self.executor_thread.start()
    
    def stop_executor(self):
        """Stop the trade executor."""
        self.log_message("Stopping executor...")
        self.stop_event.set()
        
        if self.executor_thread:
            self.executor_thread.join(timeout=5)
        
        self.update_status(False)
        self.log_message("Executor stopped")
    
    def run_executor(self, api_key: str, cloud_url: str, broker: str):
        """Run the executor in a background thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            loop.run_until_complete(
                self.connect_and_listen(api_key, cloud_url, broker)
            )
            
        except Exception as e:
            self.log_message(f"ERROR: {e}")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            self.update_status(False)
    
    async def connect_and_listen(self, api_key: str, cloud_url: str, broker: str):
        """Connect to WebSocket and listen for signals."""
        signal_count = 0
        trade_count = 0
        
        try:
            self.log_message(f"Connecting to {cloud_url}...")
            
            async with websockets.connect(cloud_url) as websocket:
                self.websocket = websocket
                self.log_message("✓ Connected!")
                
                # Send authentication
                auth_message = {
                    'api_key': api_key,
                    'client_type': 'gui_client',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }
                await websocket.send(json.dumps(auth_message))
                self.log_message("Authentication sent")
                
                # Wait for confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                if data.get('type') == 'connection_established':
                    self.log_message(f"✓ Authentication successful (Client ID: {data.get('client_id')})")
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.update_status(True))
                    
                    # Listen for messages
                    async for message in websocket:
                        if self.stop_event.is_set():
                            break
                        
                        try:
                            data = json.loads(message)
                            msg_type = data.get('type', '')
                            
                            if msg_type == 'trading_signal':
                                signal_count += 1
                                signal_data = data.get('data', {})
                                
                                # Update UI in main thread
                                self.root.after(0, lambda s=signal_data: self.add_signal_to_monitor(s))
                                self.root.after(0, lambda c=signal_count: self.signal_count_label.config(text=f"Signals Received: {c}"))
                                
                                self.log_message(f"📊 Signal #{signal_count}: {signal_data.get('strategy_name')} - {signal_data.get('symbol')} - {signal_data.get('signal_type')}")
                                
                                # Simulate trade execution (in real implementation, call broker API)
                                if broker != 'simulation':
                                    self.log_message(f"   → Executing trade on {broker.upper()}...")
                                    # TODO: Integrate with actual broker API
                                    trade_count += 1
                                    self.root.after(0, lambda t=trade_count: self.trade_count_label.config(text=f"Trades Executed: {t}"))
                                
                            elif msg_type == 'pong':
                                pass  # Heartbeat
                            
                            else:
                                self.log_message(f"Unknown message type: {msg_type}")
                        
                        except json.JSONDecodeError:
                            self.log_message("ERROR: Invalid JSON received")
                        except Exception as e:
                            self.log_message(f"ERROR processing message: {e}")
        
        except (ConnectionClosed, ConnectionClosedError) as e:
            self.log_message(f"Connection closed: {e}")
        except Exception as e:
            self.log_message(f"Connection error: {e}")
            import traceback
            self.log_message(traceback.format_exc())
        finally:
            self.websocket = None
            self.root.after(0, lambda: self.update_status(False))


def main():
    """Main entry point."""
    root = tk.Tk()
    app = QuantDingerGUI(root)
    
    # Set window icon (optional)
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    root.mainloop()


if __name__ == "__main__":
    main()
