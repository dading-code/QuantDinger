"""
HTTP API Client for QuantDinger Cloud

Handles user authentication and API key management.
"""

import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CloudAPIClient:
    """
    HTTP client for interacting with QuantDinger Cloud API.
    
    Features:
    - User login/authentication
    - API key creation and management
    - Session token management
    """
    
    def __init__(self, base_url: str = "http://localhost:5000/api"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the QuantDinger Cloud API
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
    
    def login(self, username: str, password: str) -> bool:
        """
        Login to QuantDinger Cloud.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            url = f"{self.base_url}/auth/login"
            response = self.session.post(url, json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    # Store token
                    self.token = data['data'].get('token')
                    self.user_info = data['data'].get('user')
                    
                    # Set authorization header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}'
                    })
                    
                    logger.info(f"Login successful: {username}")
                    return True
            
            logger.error(f"Login failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def create_api_key(self, key_name: str = 'Default', 
                      description: str = '', 
                      expires_days: int = 365) -> Optional[Dict[str, Any]]:
        """
        Create a new API key for the current user.
        
        Args:
            key_name: Name for the API key
            description: Description
            expires_days: Number of days until expiration (0 for no expiry)
            
        Returns:
            API key information including the key itself, or None if failed
        """
        if not self.token:
            logger.error("Not logged in")
            return None
        
        try:
            url = f"{self.base_url}/user/api-key/create"
            response = self.session.post(url, json={
                'key_name': key_name,
                'description': description,
                'expires_days': expires_days
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    logger.info("API key created successfully")
                    return data['data']
            
            logger.error(f"Failed to create API key: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Create API key error: {e}")
            return None
    
    def list_api_keys(self) -> Optional[list]:
        """
        List all API keys for the current user.
        
        Returns:
            List of API key information, or None if failed
        """
        if not self.token:
            logger.error("Not logged in")
            return None
        
        try:
            url = f"{self.base_url}/user/api-key/list"
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    return data['data'].get('keys', [])
            
            logger.error(f"Failed to list API keys: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"List API keys error: {e}")
            return None
    
    def revoke_api_key(self, key_id: int) -> bool:
        """
        Revoke (deactivate) an API key.
        
        Args:
            key_id: ID of the API key to revoke
            
        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            logger.error("Not logged in")
            return False
        
        try:
            url = f"{self.base_url}/user/api-key/revoke"
            response = self.session.post(url, json={'key_id': key_id})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    logger.info(f"API key {key_id} revoked")
                    return True
            
            logger.error(f"Failed to revoke API key: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Revoke API key error: {e}")
            return False
    
    def delete_api_key(self, key_id: int) -> bool:
        """
        Delete an API key permanently.
        
        Args:
            key_id: ID of the API key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.token:
            logger.error("Not logged in")
            return False
        
        try:
            url = f"{self.base_url}/user/api-key/delete"
            response = self.session.delete(url, json={'key_id': key_id})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    logger.info(f"API key {key_id} deleted")
                    return True
            
            logger.error(f"Failed to delete API key: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Delete API key error: {e}")
            return False
    
    def logout(self):
        """Logout and clear session."""
        self.token = None
        self.user_info = None
        self.session.headers.pop('Authorization', None)
        logger.info("Logged out")
