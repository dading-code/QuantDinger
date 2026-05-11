"""
Main GUI Application

Tkinter-based graphical interface for the QuantDinger Local Trade Client.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import asyncio
import threading
from datetime import datetime
from typing import Optional

from src.core.config import ConfigManager
from src.core.signal_client import SignalClient
from src.core.risk_manager import RiskManager
from src.core.signal_processor import SignalProcessor
from src.brokers.simulation import SimulationBroker
from src.brokers import MT5Broker, IBKRBroker, MT5_AVAILABLE, IBKR_AVAILABLE


class QuantDingerApp:
    """Main application class for the GUI."""
    
    def __init__(self):
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("QuantDinger 本地交易客户端 v2.0 - API Key模式")
        self.root.geometry("1200x800")
        
        # Configuration
        self.config_mgr = ConfigManager("config.json")
        
        # Signal client
        self.signal_client: Optional[SignalClient] = None
        self.client_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Trading components
        self.broker = None
        self.risk_manager = None
        self.signal_processor = None
        
        # Statistics
        self.signal_count = 0
        self.trade_count = 0
        
        # Create UI
        self._create_ui()
        self._load_config()
    
    def _create_ui(self):
        """Create all UI components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Configuration section
        self._create_config_section(main_frame)
        
        # Status section
        self._create_status_section(main_frame)
        
        # Control buttons
        self._create_control_section(main_frame)
        
        # Signal monitor
        self._create_signal_monitor(main_frame)
        
        # Log viewer
        self._create_log_viewer(main_frame)
    
    def _create_config_section(self, parent):
        """Create configuration section."""
        frame = ttk.LabelFrame(parent, text="配置设置", padding="10")
        frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        # Cloud API URL
        ttk.Label(frame, text="云端地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cloud_url_var = tk.StringVar(value="http://39.105.150.99:8888/api")
        entry = ttk.Entry(frame, textvariable=self.cloud_url_var, width=50)
        entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # WebSocket URL
        ttk.Label(frame, text="WS 地址:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ws_url_var = tk.StringVar(value="ws://39.105.150.99:8888/ws")
        entry = ttk.Entry(frame, textvariable=self.ws_url_var, width=50)
        entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # API Key
        ttk.Label(frame, text="API 密钥:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.api_key_var, width=50, show='*')
        entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Help text
        help_text = "💡 提示：请在Web管理后台（个人中心-交易所配置）获取API Key"
        ttk.Label(frame, text=help_text, foreground="gray", font=('Arial', 8)).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0)
        )
        
        # Separator
        ttk.Separator(frame, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Broker
        ttk.Label(frame, text="券商类型:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.broker_var = tk.StringVar(value="simulation")
        combo = ttk.Combobox(frame, textvariable=self.broker_var,
                            values=['simulation', 'mt5', 'ibkr'],
                            state='readonly', width=20)
        combo.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save button
        btn = ttk.Button(frame, text="💾 保存配置", command=self._save_config)
        btn.grid(row=5, column=2, padx=5, pady=5)
    
    def _create_status_section(self, parent):
        """Create status display section."""
        frame = ttk.LabelFrame(parent, text="连接状态", padding="10")
        frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status indicator
        self.status_label = ttk.Label(frame, text="● 未连接",
                                     foreground="red", font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # Statistics
        self.signal_label = ttk.Label(frame, text="信号数: 0")
        self.signal_label.grid(row=0, column=1, sticky=tk.W, padx=20)
        
        self.trade_label = ttk.Label(frame, text="交易数: 0")
        self.trade_label.grid(row=0, column=2, sticky=tk.W, padx=20)
    
    def _create_control_section(self, parent):
        """Create control buttons."""
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_btn = ttk.Button(frame, text="▶ 启动", command=self._start_client)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(frame, text="⏹ 停止", command=self._stop_client,
                                   state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame, text="🗑 清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="📤 导出日志", command=self._export_logs).pack(side=tk.LEFT, padx=5)
    
    def _create_signal_monitor(self, parent):
        """Create signal monitoring listbox."""
        frame = ttk.LabelFrame(parent, text="实时信号", padding="10")
        frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(0, 5))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.signal_listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, height=15)
        self.signal_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.signal_listbox.yview)
    
    def _create_log_viewer(self, parent):
        """Create log text viewer."""
        frame = ttk.LabelFrame(parent, text="运行日志", padding="10")
        frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=(5, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='disabled',
                                                  font=('Consolas', 9), height=15,
                                                  yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.log_text.yview)
    
    def _load_config(self):
        """Load configuration into UI."""
        self.api_key_var.set(self.config_mgr.get('api_key', ''))
        self.cloud_url_var.set(self.config_mgr.get('cloud_api_url', 'http://39.105.150.99:8888/api'))
        self.ws_url_var.set(self.config_mgr.get('cloud_url', 'ws://39.105.150.99:8888/ws'))
        self.broker_var.set(self.config_mgr.get('broker', 'simulation'))
    
    def _save_config(self):
        """Save configuration from UI."""
        self.config_mgr.set('api_key', self.api_key_var.get())
        self.config_mgr.set('cloud_api_url', self.cloud_url_var.get())
        self.config_mgr.set('cloud_url', self.ws_url_var.get())
        self.config_mgr.set('broker', self.broker_var.get())
        
        try:
            self.config_mgr.save()
            self._log("✓ 配置已保存")
            messagebox.showinfo("成功", "配置保存成功！")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def _log(self, message: str):
        """Add message to log."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {message}\n"
        
        self.log_text.configure(state='normal')
        self.log_text.insert('end', formatted)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')
    
    def _clear_logs(self):
        """Clear log display."""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
        self._log("日志已清空")
    
    def _export_logs(self):
        """Export logs to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get('1.0', 'end'))
                messagebox.showinfo("成功", f"日志已导出到 {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def _update_status(self, connected: bool):
        """Update connection status display."""
        if connected:
            self.status_label.config(text="● 已连接", foreground="green")
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        else:
            self.status_label.config(text="● 未连接", foreground="red")
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def _add_signal(self, signal_data: dict):
        """Add signal to monitor."""
        signal = signal_data.get('data', {})
        timestamp = signal_data.get('timestamp', '')[:19]
        strategy = signal.get('strategy_name', 'N/A')
        symbol = signal.get('symbol', 'N/A')
        signal_type = signal.get('signal_type', 'N/A')
        
        entry = f"{timestamp} | {strategy} | {symbol} | {signal_type}"
        self.signal_listbox.insert('end', entry)
        self.signal_listbox.see('end')
    
    def _start_client(self):
        """Start the signal client."""
        api_key = self.api_key_var.get().strip()
        ws_url = self.ws_url_var.get().strip()
        broker_type = self.broker_var.get().strip()
        
        if not api_key:
            messagebox.showerror("错误", "请先在Web管理后台获取API Key并填入配置")
            return
        
        if not ws_url:
            messagebox.showerror("错误", "请输入 WebSocket 地址")
            return
        
        self._log(f"启动客户端: 券商={broker_type}")
        self.stop_event.clear()
        
        # Start in background thread
        self.client_thread = threading.Thread(
            target=self._run_client,
            args=(api_key, ws_url, broker_type),
            daemon=True
        )
        self.client_thread.start()
    
    def _stop_client(self):
        """Stop the signal client."""
        self._log("正在停止客户端...")
        self.stop_event.set()
        
        if self.client_thread:
            self.client_thread.join(timeout=5)
        
        self._update_status(False)
        self._log("客户端已停止")
    
    def _run_client(self, api_key: str, cloud_url: str, broker_type: str):
        """Run signal client in background thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Initialize broker
            self._log(f"初始化券商: {broker_type}")
            
            if broker_type == 'simulation':
                self.broker = SimulationBroker(config={'initial_balance': 10000.0})
                loop.run_until_complete(self.broker.connect())
                self._log("✓ 模拟券商已连接")
            
            elif broker_type == 'mt5':
                if not MT5_AVAILABLE:
                    error_msg = "❌ MT5库未安装，请使用: pip install MetaTrader5"
                    self._log(error_msg)
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    raise RuntimeError(error_msg)
                            
                mt5_config = self.config_mgr.get('mt5', {})
                self.broker = MT5Broker(config=mt5_config)
                connected = loop.run_until_complete(self.broker.connect())
                if not connected:
                    error_msg = "❌ MT5连接失败，请检查MT5终端是否运行且已登录账户"
                    self._log(error_msg)
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    raise RuntimeError(error_msg)
                            
                self._log("✓ MT5券商已连接")
                        
            elif broker_type == 'ibkr':
                if not IBKR_AVAILABLE:
                    error_msg = "❌ ib_insync库未安装，请使用: pip install ib_insync"
                    self._log(error_msg)
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    raise RuntimeError(error_msg)
                            
                ibkr_config = self.config_mgr.get('ibkr', {})
                self.broker = IBKRBroker(config=ibkr_config)
                connected = loop.run_until_complete(self.broker.connect())
                if not connected:
                    error_msg = "❌ IBKR连接失败，请检查TWS/Gateway是否运行且端口正确"
                    self._log(error_msg)
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    raise RuntimeError(error_msg)
                            
                self._log("✓ IBKR券商已连接")
                        
            else:
                error_msg = f" 不支持的券商类型: {broker_type}。支持的类型: simulation, mt5, ibkr"
                self._log(error_msg)
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                raise RuntimeError(error_msg)
            
            # Initialize risk manager
            risk_config = self.config_mgr.get('risk_management', {})
            self.risk_manager = RiskManager(risk_config)
            self._log("✓ 风险管理引擎已启动")
            
            # Initialize signal processor
            self.signal_processor = SignalProcessor(self.broker, self.risk_manager)
            self._log("✓ 信号处理器已就绪")
            
            # Create signal client with callbacks
            client = SignalClient(
                api_key=api_key,
                cloud_url=cloud_url,
                on_signal=self._on_signal,
                on_connect=lambda _: self.root.after(0, lambda: self._update_status(True)),
                on_disconnect=lambda: self.root.after(0, lambda: self._update_status(False)),
            )
            
            self.signal_client = client
            loop.run_until_complete(client.connect())
            
        except Exception as e:
            self.root.after(0, lambda: self._log(f"错误: {e}"))
        finally:
            self.root.after(0, lambda: self._update_status(False))
    
    def _on_signal(self, signal_data: dict):
        """Handle received signal (called from background thread)."""
        self.signal_count += 1
        
        # Update UI in main thread
        self.root.after(0, lambda: self._add_signal(signal_data))
        self.root.after(0, lambda: self.signal_label.config(text=f"Signals: {self.signal_count}"))
        
        signal = signal_data.get('data', {})
        self._log(
            f"📊 信号 #{self.signal_count}: "
            f"{signal.get('strategy_name')} - "
            f"{signal.get('symbol')} - "
            f"{signal.get('signal_type')}"
        )
        
        # Execute trade if signal processor is available
        if self.signal_processor:
            try:
                # Process signal and execute trade
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    self.signal_processor.process_signal(signal_data)
                )
                loop.close()
                
                if result['status'] == 'executed':
                    self.trade_count += 1
                    self.root.after(0, lambda: self.trade_label.config(text=f"Trades: {self.trade_count}"))
                    self._log(f"✓ 交易执行成功: {result.get('trade_result', {}).get('order_id')}")
                elif result['status'] == 'rejected':
                    self._log(f"⚠️ 交易被拒绝: {result.get('reason')}")
                else:
                    self._log(f"❌ 交易错误: {result.get('reason')}")
            except Exception as e:
                self._log(f"❌ 交易执行失败: {str(e)}")
    
    def run(self):
        """Run the application."""
        self.root.mainloop()
