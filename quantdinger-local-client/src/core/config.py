"""
Configuration Manager

Handles loading, saving, and validating client configuration.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """
    Manages client configuration with file-based persistence.
    
    Configuration includes:
    - API credentials
    - Connection settings
    - Broker preferences
    - Risk management parameters
    """
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        
        # Default configuration
        self.defaults = {
            'api_key': '',
            'cloud_url': 'ws://localhost:8765/ws',
            'broker': 'simulation',
            'risk_management': {
                'max_position_size': 0.02,
                'max_daily_loss': 0.05,
                'max_open_positions': 5,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.04,
                'symbol_whitelist': [],
                'symbol_blacklist': [],
            }
        }
        
        # Load existing config
        self.load()
    
    def load(self):
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                    # Merge with defaults
                    self.config = self.defaults.copy()
                    self._deep_merge(self.config, loaded_config)
                    
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
                self.config = self.defaults.copy()
        else:
            self.config = self.defaults.copy()
    
    def save(self):
        """Save configuration to file."""
        try:
            # Ensure directory exists
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise Exception(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation: 'risk.max_position_size')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to nested key
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Set final key
        config[keys[-1]] = value
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not self.config.get('api_key'):
            return False, "API Key is required"
        
        if not self.config.get('cloud_url'):
            return False, "Cloud URL is required"
        
        # Validate broker type
        valid_brokers = ['simulation', 'mt5', 'ibkr']
        broker = self.config.get('broker', '')
        if broker not in valid_brokers:
            return False, f"Invalid broker: {broker}. Must be one of: {', '.join(valid_brokers)}"
        
        # Validate risk parameters
        risk = self.config.get('risk_management', {})
        if risk.get('max_position_size', 0) <= 0:
            return False, "Max position size must be positive"
        
        if risk.get('max_daily_loss', 0) <= 0:
            return False, "Max daily loss must be positive"
        
        return True, ""
    
    def reset_to_defaults(self):
        """Reset configuration to default values."""
        self.config = self.defaults.copy()
        self.save()
    
    def _deep_merge(self, base: dict, update: dict):
        """
        Recursively merge update dict into base dict.
        
        Args:
            base: Base dictionary
            update: Update dictionary
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """Allow dict-like assignment."""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return key in self.config
