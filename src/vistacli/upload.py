"""
Upload functionality for Vista Social media library.
"""
import logging
import mimetypes
import os
import random
import time
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

from .auth import VSAuth

logger = logging.getLogger(__name__)

# Supported image types for Vista Social
SUPPORTED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/webp': ['.webp'],
    'image/bmp': ['.bmp'],
    'image/tiff': ['.tiff', '.tif'],
    'image/svg+xml': ['.svg']
}

SUPPORTED_EXTENSIONS = [ext for extensions in SUPPORTED_IMAGE_TYPES.values() for ext in extensions]


class VSUploader:
    """Handles file uploads to Vista Social media library."""
    
    def __init__(self, auth: VSAuth):
        self.auth = auth
        self.client = auth.create_session()
    
    def upload_file(self, file_path: str, subfolder: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to Vista Social media library.
        
        Args:
            file_path: Path to the file to upload
            subfolder: Optional subfolder ID to place the uploaded asset in
            
        Returns:
            Dict containing upload result information
            
        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If upload fails
        """
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Validate file type
        self._validate_file_type(file_path)
        
        # Generate temp ID (random number for now)
        temp_id = self._generate_temp_id()
        
        logger.debug(f"vsput: Starting upload for {file_path} with temp_id {temp_id}")
        
        # Step 1: Start upload
        upload_info = self._start_upload(file_path, temp_id, subfolder)
        
        # Step 2: Upload file to S3
        self._upload_to_s3(file_path, upload_info['upload_url'])
        
        # Step 3: OPTIONS request (CORS preflight)
        self._options_request(upload_info['upload_url'])
        
        # Step 4: Finish upload
        result = self._finish_upload(temp_id, upload_info['media_gid'])
        
        # Step 5: Fetch metadata from CloudFront (optional but completes the flow)
        metadata = None
        if 'meta_url' in upload_info:
            metadata = self._fetch_metadata(upload_info['meta_url'])
        
        # Step 6: Batch update to associate file with folder and metadata
        self._batch_update(upload_info['media_gid'], metadata, subfolder)
        
        logger.info(f"vsput: Successfully uploaded {file_path}")
        return result
    
    def _validate_file_type(self, file_path: Path) -> None:
        """Validate that the file type is supported."""
        # Check file extension
        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {extension}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or mime_type not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(f"Unsupported MIME type: {mime_type}. Supported: {', '.join(SUPPORTED_IMAGE_TYPES.keys())}")
        
        logger.debug(f"vsput: Validated file type: {mime_type} ({extension})")
    
    def _generate_temp_id(self) -> str:
        """Generate a temporary ID for the upload."""
        # For now, use current timestamp + random number
        # This can be refined based on actual Vista Social requirements
        timestamp = int(time.time() * 1000)
        random_num = random.randint(1000, 9999)
        return str(timestamp + random_num)
    
    def _start_upload(self, file_path: Path, temp_id: str, subfolder: Optional[str] = None) -> Dict[str, Any]:
        """Step 1: Start the upload process."""
        url = f"{self.auth.BASE_URL}/api/publishing/media/upload/start"
        
        params = {
            'tempId': temp_id,
            'replacement_type': ''
        }
        
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.auth.BASE_URL}/media/{subfolder}' if subfolder else f'{self.auth.BASE_URL}/media',
            'Content-Type': 'application/json',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=4',
            'TE': 'trailers'
        }
        
        # Don't duplicate headers - the client already has them
        
        # Build request body with file metadata
        file_size = file_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
            
        request_body = {
            "name": file_path.name,
            "mimetype": mime_type,
            "size": file_size,
            "hibernated": True
        }
        
        logger.debug(f"vsput: POST {url}")
        logger.debug(f"vsput: Headers: {headers}")
        logger.debug(f"vsput: Params: {params}")
        logger.debug(f"vsput: Request body: {request_body}")
        
        response = self.client.post(url, params=params, headers=headers, json=request_body)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"vsput: Response status: {response.status_code}")
        logger.debug(f"vsput: Response headers: {dict(response.headers)}")
        logger.debug(f"vsput: Response body: {data}")
        
        return data
    
    def _upload_to_s3(self, file_path: Path, upload_url: str) -> None:
        """Step 2: Upload file to S3."""
        logger.debug(f"vsput: Uploading {file_path} to S3")
        
        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Determine content type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.auth.BASE_URL}/',
            'Content-Type': mime_type,
            'Content-Disposition': 'inline',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        logger.debug(f"vsput: PUT {upload_url}")
        logger.debug(f"vsput: Headers: {headers}")
        logger.debug(f"vsput: Content-Length: {len(file_content)}")
        
        # Use a separate client for S3 upload (no cookies needed)
        with httpx.Client() as s3_client:
            response = s3_client.put(upload_url, content=file_content, headers=headers)
            response.raise_for_status()
        
        logger.debug(f"vsput: S3 upload response status: {response.status_code}")
        logger.debug(f"vsput: S3 upload response headers: {dict(response.headers)}")
    
    def _options_request(self, upload_url: str) -> None:
        """Step 3: OPTIONS request for CORS preflight."""
        logger.debug(f"vsput: OPTIONS request for CORS preflight")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'content-disposition,content-type',
            'Referer': f'{self.auth.BASE_URL}/',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Priority': 'u=4'
        }
        
        # Use a separate client for OPTIONS request
        with httpx.Client() as options_client:
            response = options_client.options(upload_url, headers=headers)
            response.raise_for_status()
        
        logger.debug(f"vsput: OPTIONS response status: {response.status_code}")
    
    def _finish_upload(self, temp_id: str, media_gid: str) -> Dict[str, Any]:
        """Step 4: Finish the upload process."""
        url = f"{self.auth.BASE_URL}/api/publishing/media/upload/finish"
        
        params = {
            'tempId': temp_id,
            'hibernated': 'true',
            'id': media_gid,
            'success': 'true',
            'replacement_type': ''
        }
        
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.auth.BASE_URL}/media',
            'Content-Type': 'application/json',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=4'
        }
        
        # Don't duplicate headers - the client already has them
        
        logger.debug(f"vsput: POST {url}")
        logger.debug(f"vsput: Headers: {headers}")
        logger.debug(f"vsput: Params: {params}")
        
        response = self.client.post(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"vsput: Response status: {response.status_code}")
        logger.debug(f"vsput: Response headers: {dict(response.headers)}")
        logger.debug(f"vsput: Response body: {data}")
        
        return data 
    
    def _fetch_metadata(self, meta_url: str) -> Optional[Dict[str, Any]]:
        """Step 5: Fetch metadata from CloudFront."""
        logger.debug(f"vsput: Fetching metadata from CloudFront")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.auth.BASE_URL}/',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Priority': 'u=4'
        }
        
        logger.debug(f"vsput: GET {meta_url}")
        logger.debug(f"vsput: Headers: {headers}")
        
        # Use a separate client for CloudFront request (no cookies needed)
        with httpx.Client() as cf_client:
            response = cf_client.get(meta_url, headers=headers)
            response.raise_for_status()
        
        data = response.json()
        logger.debug(f"vsput: CloudFront response status: {response.status_code}")
        logger.debug(f"vsput: CloudFront response headers: {dict(response.headers)}")
        logger.debug(f"vsput: CloudFront metadata: {data}")
        
        return data
    
    def _batch_update(self, media_gid: str, metadata: Optional[Dict[str, Any]], subfolder: Optional[str] = None) -> None:
        """Step 6: Batch update to associate file with folder and metadata."""
        logger.debug(f"vsput: Batch updating media {media_gid}")
        
        url = f"{self.auth.BASE_URL}/api/publishing/media/batch"
        
        # Build the batch update payload
        batch_item = {
            "media_gid": media_gid,
            "labels": [],
            "description": "",
            "title": "",
            "entity_gids": ["1b0e4760-3503-11f0-8a9e-d56e42db09d2"],  # Default entity
            "media_path": [subfolder] if subfolder else []
        }
        
        # Add metadata if available
        if metadata:
            batch_item.update({
                "width": metadata.get("width"),
                "height": metadata.get("height"),
                "aspect_ratio": metadata.get("aspect_ratio"),
                "codec_name": metadata.get("codec_name"),
                "codec_long_name": metadata.get("codec_long_name"),
                "r_frame_rate": metadata.get("r_frame_rate"),
                "time_base": metadata.get("time_base"),
                "pix_fmt": metadata.get("pix_fmt")
            })
        
        payload = [batch_item]
        
        headers = {
            'User-Agent': 'VistaSocialUI',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.auth.BASE_URL}/media/{subfolder}' if subfolder else f'{self.auth.BASE_URL}/media',
            'Content-Type': 'application/json',
            'Origin': self.auth.BASE_URL,
            'DNT': '1',
            'Sec-GPC': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=4'
        }
        
        # Don't duplicate headers - the client already has them
        
        logger.debug(f"vsput: PUT {url}")
        logger.debug(f"vsput: Headers: {headers}")
        logger.debug(f"vsput: Payload: {payload}")
        
        response = self.client.put(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"vsput: Batch update response status: {response.status_code}")
        logger.debug(f"vsput: Batch update response headers: {dict(response.headers)}")
        logger.debug(f"vsput: Batch update response body: {data}") 