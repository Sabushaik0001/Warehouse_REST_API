"""
Azure Blob Storage integration
"""

from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """
    Initialize and return Azure Blob Service Client
    
    Returns:
        BlobServiceClient: Azure blob service client instance
    """
    try:
        # Create credential using service principal
        credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        )
        
        # Initialize Blob Service Client
        account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        
        return blob_service_client
        
    except Exception as e:
        logger.error(f"Error initializing Azure Blob Service Client: {e}")
        raise


# Global blob service client instance
blob_service_client = get_blob_service_client()
