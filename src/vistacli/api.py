"""Vista Social API client."""

import logging
from typing import Dict, List, Optional, Any

import httpx

from .auth import VSAuth

logger = logging.getLogger(__name__)


class VSApi:
    """Vista Social API client."""
    
    BASE_URL = "https://vistasocial.com"
    
    def __init__(self, auth: Optional[VSAuth] = None):
        """Initialize the API client.
        
        Args:
            auth: Authentication handler. If None, creates a new one.
        """
        self.auth = auth or VSAuth()
        self.client: Optional[httpx.Client] = None
        
    def __enter__(self):
        """Context manager entry."""
        self.client = self.auth.create_session()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.client:
            self.client.close()
            
    def _ensure_client(self):
        """Ensure client is initialized."""
        if not self.client:
            self.client = self.auth.create_session()
    
    def get_folders(self, media_path: Optional[str] = None, query: str = "") -> List[Dict[str, Any]]:
        """Get list of folders.
        
        Args:
            media_path: Optional parent folder ID for subfolder listing
            query: Optional search query
            
        Returns:
            List of folder dictionaries
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        self._ensure_client()
        
        url = f"{self.BASE_URL}/api/publishing/media/folders"
        params = {"q": query}
        if media_path:
            params["media_path"] = media_path
            
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://vistasocial.com/media',
            'Content-Type': 'application/json',
            'DNT': '1',
            'Sec-GPC': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=4'
        }
        
        try:
            logger.debug(f"vsdir: GET {url}")
            logger.debug(f"vsdir: Headers: {headers}")
            logger.debug(f"vsdir: Params: {params}")
            
            response = self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            logger.debug(f"vsdir: Response status: {response.status_code}")
            logger.debug(f"vsdir: Response headers: {dict(response.headers)}")
            
            data = response.json()
            logger.debug(f"vsdir: Response body: {data}")
            
            folders = data.get('data', [])
            logger.info(f"vsdir: retrieved {len(folders)} folders")
            return folders
            
        except httpx.HTTPError as e:
            logger.error(f"vsdir: failed to get folders: {e}")
            raise
    
    def create_folder(self, name: str, description: str = "", labels: Optional[List[str]] = None, entity_gids: Optional[List[str]] = None, media_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder.
        
        Args:
            name: Title of the folder to create
            description: Description of the folder
            labels: List of labels/tags for the folder
            entity_gids: List of entity GIDs (group IDs) for the folder
            media_path: Optional parent folder ID for creating subfolders
            
        Returns:
            Created folder data
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        self._ensure_client()
        
        # Actual Vista Social API endpoint
        url = f"{self.BASE_URL}/api/publishing/media/folder"
        
        payload = {
            "title": name,
            "description": description,
            "media_path": [media_path] if media_path else None,
            "labels": labels or [],
            "entity_gids": entity_gids or []
        }
        
        # Update headers to match Vista Social's expected format
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'https://vistasocial.com/media/{media_path}' if media_path else 'https://vistasocial.com/media?',
            'Content-Type': 'application/json',
            'Origin': 'https://vistasocial.com',
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=0',
            'TE': 'trailers'
        }
        
        try:
            # Log request details at DEBUG level
            logger.debug(f"vsdir: POST {url}")
            logger.debug(f"vsdir: Headers: {headers}")
            logger.debug(f"vsdir: Payload: {payload}")
            logger.debug(f"vsdir: Request headers: {dict(self.client.headers)}")
            
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Log response details at DEBUG level
            logger.debug(f"vsdir: Response status: {response.status_code}")
            logger.debug(f"vsdir: Response headers: {dict(response.headers)}")
            
            data = response.json()
            logger.debug(f"vsdir: Response body: {data}")
            
            # Check for error in response body
            if 'error' in data:
                error_msg = data['error']
                logger.error(f"vsdir: API returned error: {error_msg}")
                raise httpx.HTTPStatusError(f"API Error: {error_msg}", request=response.request, response=response)
            
            logger.info(f"vsdir: created folder '{name}'")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"vsdir: failed to create folder '{name}': {e}")
            raise
    

    
    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder.
        
        Args:
            folder_id: ID of the folder to delete
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        self._ensure_client()
        
        url = f"{self.BASE_URL}/api/publishing/media/folder/{folder_id}"
        
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://vistasocial.com/media?',
            'Content-Type': 'application/json',
            'Origin': 'https://vistasocial.com',
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=0'
        }
        
        try:
            logger.debug(f"vsdir: DELETE {url}")
            logger.debug(f"vsdir: Headers: {headers}")
            
            response = self.client.delete(url, headers=headers)
            response.raise_for_status()
            
            logger.debug(f"vsdir: Response status: {response.status_code}")
            logger.debug(f"vsdir: Response headers: {dict(response.headers)}")
            
            logger.info(f"vsdir: deleted folder '{folder_id}'")
            
        except httpx.HTTPError as e:
            logger.error(f"vsdir: failed to delete folder '{folder_id}': {e}")
            raise 