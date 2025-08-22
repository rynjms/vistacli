"""Authentication module for Vista Social."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import browser_cookie3
import httpx

logger = logging.getLogger(__name__)


class VSAuth:
    """Vista Social authentication handler."""
    
    BASE_URL = "https://vistasocial.com"
    
    def __init__(self, auth_file: Optional[Path] = None):
        """Initialize the auth handler.
        
        Args:
            auth_file: Path to auth file. Defaults to ~/.vsauth
        """
        if auth_file is None:
            auth_file = Path.home() / ".vsauth"
        self.auth_file = auth_file
        
    def extract_cookies(self) -> Dict[str, str]:
        """Extract cookies from Firefox for vistasocial.com.
        
        Returns:
            Dictionary of cookie name-value pairs
            
        Raises:
            RuntimeError: If no cookies found for vistasocial.com
        """
        try:
            # Extract cookies from Firefox
            cookies = browser_cookie3.firefox(domain_name='vistasocial.com')
            
            # Convert to dictionary
            cookie_dict = {cookie.name: cookie.value for cookie in cookies}
            
            if not cookie_dict:
                raise RuntimeError("No cookies found for vistasocial.com in Firefox")
                
            logger.info(f"vsauth: extracted {len(cookie_dict)} cookies from Firefox")
            return cookie_dict
            
        except Exception as e:
            logger.error(f"vsauth: failed to extract cookies: {e}")
            raise RuntimeError(f"Failed to extract cookies: {e}")
    
    def save_cookies(self, cookies: Dict[str, str]) -> None:
        """Save cookies to auth file.
        
        Args:
            cookies: Dictionary of cookie name-value pairs
        """
        try:
            # Ensure parent directory exists
            self.auth_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save cookies as JSON
            with open(self.auth_file, 'w') as f:
                json.dump(cookies, f, indent=2)
                
            logger.info(f"vsauth: saved cookies to {self.auth_file}")
            
        except Exception as e:
            logger.error(f"vsauth: failed to save cookies: {e}")
            raise RuntimeError(f"Failed to save cookies: {e}")
    
    def load_cookies(self) -> Dict[str, str]:
        """Load cookies from auth file.
        
        Returns:
            Dictionary of cookie name-value pairs
            
        Raises:
            FileNotFoundError: If auth file doesn't exist
            RuntimeError: If auth file is invalid
        """
        try:
            if not self.auth_file.exists():
                raise FileNotFoundError(f"Auth file not found: {self.auth_file}")
                
            with open(self.auth_file, 'r') as f:
                cookies = json.load(f)
                
            logger.info(f"vsauth: loaded {len(cookies)} cookies from {self.auth_file}")
            return cookies
            
        except json.JSONDecodeError as e:
            logger.error(f"vsauth: invalid JSON in auth file: {e}")
            raise RuntimeError(f"Invalid auth file format: {e}")
        except Exception as e:
            logger.error(f"vsauth: failed to load cookies: {e}")
            raise RuntimeError(f"Failed to load cookies: {e}")
    
    def create_session(self) -> httpx.Client:
        """Create an httpx client with loaded cookies.
        
        Returns:
            httpx.Client configured with Vista Social cookies
        """
        cookies = self.load_cookies()
        
        # Create client with Vista Social UI headers
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Sec-GPC': '1',
            'Connection': 'keep-alive',
        }
        
        client = httpx.Client(
            headers=headers,
            cookies=cookies,
            follow_redirects=True,
            timeout=30.0
        )
        
        logger.info("vsauth: created session with browser-like headers")
        logger.debug(f"vsauth: Loaded cookies: {list(cookies.keys())}")
        logger.debug(f"vsauth: Session headers: {headers}")
        return client 