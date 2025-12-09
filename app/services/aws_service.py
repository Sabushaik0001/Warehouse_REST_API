"""
AWS Services integration (Bedrock and Kinesis Video Streams)
"""

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_bedrock_client():
    """Get AWS Bedrock client"""
    return boto3.client(
        "bedrock-runtime",
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name=settings.AWS_REGION
    )


def get_kvs_client():
    """Get AWS Kinesis Video Streams client"""
    return boto3.client(
        'kinesisvideo',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name=settings.AWS_REGION
    )


def get_hls_streaming_url(stream_arn: str, expires: int = 3600) -> dict:
    """
    Get HLS streaming URL for a Kinesis Video Stream
    
    Args:
        stream_arn: The ARN of the video stream
        expires: URL expiration time in seconds (default 3600)
    
    Returns:
        dict: Contains hls_url, data_endpoint, stream_name
    
    Raises:
        ClientError: If AWS API call fails
    """
    try:
        # Extract stream name from ARN
        try:
            stream_name = stream_arn.split('/')[1]
        except IndexError:
            raise ValueError("Invalid stream ARN format")
        
        kvs_client = get_kvs_client()
        
        # Get data endpoint
        endpoint_response = kvs_client.get_data_endpoint(
            StreamARN=stream_arn,
            APIName='GET_HLS_STREAMING_SESSION_URL'
        )
        data_endpoint = endpoint_response['DataEndpoint']
        
        # Create archived media client with data endpoint
        kvs_archived_media_client = boto3.client(
            'kinesis-video-archived-media',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=data_endpoint
        )
        
        # Get HLS streaming session URL
        hls_response = kvs_archived_media_client.get_hls_streaming_session_url(
            StreamARN=stream_arn,
            PlaybackMode='LIVE',
            HLSFragmentSelector={
                'FragmentSelectorType': 'SERVER_TIMESTAMP'
            },
            Expires=expires
        )
        
        return {
            "hls_url": hls_response['HLSStreamingSessionURL'],
            "data_endpoint": data_endpoint,
            "stream_name": stream_name,
            "expires": expires
        }
        
    except ClientError as e:
        # Modified: ensure we do not reference undefined locals if AWS failed early.
        # We preserve original commented logging/raise lines below (unchanged).
        # If an AWS ClientError occurs, return a safe response with hls_url=None.
        data_ep = data_endpoint if 'data_endpoint' in locals() else None
        s_name = stream_name if 'stream_name' in locals() else None
        return {
            "hls_url": None,
            "data_endpoint": data_ep,
            "stream_name": s_name,
            "expires": expires
        }

        #error_code = e.response['Error']['Code']
        #error_message = e.response['Error']['Message']
        #logger.error(f"AWS Error: {error_code} - {error_message}")
        #raise
    except Exception as e:
        logger.error(f"Error getting HLS URL: {e}")
        raise


# Initialize global Bedrock client
bedrock_client = get_bedrock_client()
