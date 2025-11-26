"""
Azure Blob Storage service for managing user images and videos.
This service handles uploading and retrieving images and videos for candidates.
"""
import os
import logging
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContentSettings
from core.config import settings

logger = logging.getLogger(__name__)


class BlobStorageService:
    """
    Azure Blob Storage service for managing user images and videos.
    This module can be easily integrated into existing FastAPI backends.
    """
    
    def __init__(self):
        """Initialize the blob storage client and containers."""
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.image_container = settings.IMAGE_CONTAINER_NAME
        self.video_container = settings.VIDEO_CONTAINER_NAME
        
        # Create containers if they don't exist
        self._ensure_containers_exist()
    
    def _ensure_containers_exist(self):
        """Create containers if they don't exist."""
        try:
            self.blob_service_client.create_container(self.image_container)
            logger.info(f"Created container: {self.image_container}")
        except Exception as e:
            logger.debug(f"Container {self.image_container} already exists or error: {e}")
        
        try:
            self.blob_service_client.create_container(self.video_container)
            logger.info(f"Created container: {self.video_container}")
        except Exception as e:
            logger.debug(f"Container {self.video_container} already exists or error: {e}")
    
    def upload_image(self, candidate_id: str, file_content: bytes, filename: str) -> dict:
        """
        Upload an image to blob storage.
        
        Args:
            candidate_id: Unique identifier for the candidate
            file_content: Image file content as bytes
            filename: Original filename
            
        Returns:
            dict: Upload result with blob URL and metadata
        """
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"Invalid image format. Allowed: {', '.join(allowed_extensions)}")
        
        # Create blob name: candidate_id + original extension
        blob_name = f"{candidate_id}{file_ext}"
        
        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.image_container,
            blob=blob_name
        )
        
        # Set content type based on extension
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png'
        }
        content_settings = ContentSettings(content_type=content_type_map.get(file_ext, 'image/jpeg'))
        
        # Upload the blob
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings
        )
        
        logger.info(f"Image uploaded successfully for candidate_id: {candidate_id}")
        
        return {
            "candidate_id": candidate_id,
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "container": self.image_container,
            "message": "Image uploaded successfully"
        }
    
    def upload_video(self, candidate_id: str, file_content: bytes, filename: str) -> dict:
        """
        Upload a video to blob storage.
        
        Args:
            candidate_id: Unique identifier for the candidate
            file_content: Video file content as bytes
            filename: Original filename
            
        Returns:
            dict: Upload result with blob URL and metadata
        """
        # Validate file type
        allowed_extensions = ['.mp4', '.webm']
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"Invalid video format. Allowed: {', '.join(allowed_extensions)}")
        
        # Create blob name: candidate_id + original extension
        blob_name = f"{candidate_id}{file_ext}"
        
        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.video_container,
            blob=blob_name
        )
        
        # Set content type based on extension
        content_type_map = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm'
        }
        content_settings = ContentSettings(content_type=content_type_map.get(file_ext, 'video/mp4'))
        
        # Upload the blob
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings
        )
        
        logger.info(f"Video uploaded successfully for candidate_id: {candidate_id}")
        
        return {
            "candidate_id": candidate_id,
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "container": self.video_container,
            "message": "Video uploaded successfully"
        }
    
    def get_image(self, candidate_id: str) -> Optional[tuple]:
        """
        Retrieve an image from blob storage.
        
        Args:
            candidate_id: Unique identifier for the candidate
            
        Returns:
            tuple: (file_content, content_type, filename) or None if not found
        """
        # Try different image extensions
        extensions = ['.jpg', '.jpeg', '.png']
        
        for ext in extensions:
            blob_name = f"{candidate_id}{ext}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.image_container,
                blob=blob_name
            )
            
            try:
                # Check if blob exists
                if blob_client.exists():
                    # Download blob
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    properties = blob_client.get_blob_properties()
                    content_type = properties.content_settings.content_type or 'image/jpeg'
                    
                    return content, content_type, blob_name
            except Exception as e:
                logger.debug(f"Error checking blob {blob_name}: {e}")
                continue
        
        return None
    
    def get_video(self, candidate_id: str) -> Optional[tuple]:
        """
        Retrieve a video from blob storage.
        
        Args:
            candidate_id: Unique identifier for the candidate
            
        Returns:
            tuple: (file_content, content_type, filename) or None if not found
        """
        # Try different video extensions
        extensions = ['.mp4', '.webm']
        
        for ext in extensions:
            blob_name = f"{candidate_id}{ext}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.video_container,
                blob=blob_name
            )
            
            try:
                # Check if blob exists
                if blob_client.exists():
                    # Download blob
                    blob_data = blob_client.download_blob()
                    content = blob_data.readall()
                    properties = blob_client.get_blob_properties()
                    content_type = properties.content_settings.content_type or 'video/mp4'
                    
                    return content, content_type, blob_name
            except Exception as e:
                logger.debug(f"Error checking blob {blob_name}: {e}")
                continue
        
        return None

