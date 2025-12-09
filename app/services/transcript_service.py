"""
Transcript processing utilities for video chat functionality
"""

import re
import json
from typing import List, Dict, Any
from app.services.azure_service import blob_service_client
import logging

logger = logging.getLogger(__name__)


def list_transcript_files(container_name: str, prefix: str) -> List[str]:
    """
    List all transcript JSON files in Azure Blob with chunk_start in name
    
    Args:
        container_name: Azure blob container name
        prefix: Blob prefix (folder path)
    
    Returns:
        List[str]: List of blob names matching criteria
    """
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        
        return [
            blob.name for blob in blob_list
            if blob.name.endswith('.json') and 'chunk_start' in blob.name
        ]
    except Exception as e:
        logger.error(f"Error listing transcript files: {e}")
        return []


def extract_chunk_start(blob_name: str) -> int:
    """
    Extract chunk start number from blob name
    
    Args:
        blob_name: Name of the blob file
    
    Returns:
        int: Chunk start number, or infinity if not found
    """
    match = re.search(r'chunk_start-(\d+)', blob_name)
    return int(match.group(1)) if match else float('inf')


def merge_transcripts(container_name: str, blob_names: List[str]) -> Dict[str, Any]:
    """
    Merge multiple transcript JSON files into single result
    
    Args:
        container_name: Azure blob container name
        blob_names: List of blob file names to merge
    
    Returns:
        Dict[str, Any]: Merged transcript data
    """
    results = []
    sorted_names = sorted(blob_names, key=extract_chunk_start)
    container_client = blob_service_client.get_container_client(container_name)
    
    for blob_name in sorted_names:
        try:
            blob_client = container_client.get_blob_client(blob_name)
            blob_data = blob_client.download_blob()
            content = blob_data.readall().decode('utf-8')
            data = json.loads(content)
            
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping invalid JSON in {blob_name}: {e}")
        except Exception as e:
            logger.error(f"Error reading {blob_name}: {e}")
    
    return {
        "statusCode": 200,
        "videoTranscript": {
            "results": json.dumps(results),
            "count_results": []
        }
    }


def build_video_context(transcript_data: Dict[str, Any]) -> str:
    """
    Build video context string from transcript data
    
    Args:
        transcript_data: Merged transcript data
    
    Returns:
        str: Formatted video context for AI prompt
    """
    video_context = ""
    
    try:
        if "videoTranscript" in transcript_data and "results" in transcript_data["videoTranscript"]:
            results = transcript_data["videoTranscript"]["results"]
            
            if isinstance(results, str):
                results = json.loads(results)
            
            for item in results:
                if isinstance(item, dict):
                    for key in sorted(item):
                        video_context += f"**************{key}**************\n"
                        video_context += f"{item[key]}\n\n"
    except Exception as e:
        logger.error(f"Error parsing transcript: {e}")
        raise
    
    return video_context


def parse_blob_url(transcript_blob_url: str) -> tuple:
    """
    Parse Azure Blob URL to extract container name and prefix
    
    Args:
        transcript_blob_url: Full blob URL
    
    Returns:
        tuple: (container_name, blob_prefix)
    
    Raises:
        ValueError: If URL format is unsupported
    """
    if transcript_blob_url.startswith("https://"):
        url_parts = transcript_blob_url.replace("https://", "").split("/")
        container_name = url_parts[1]
        
        # Remove file name if present and get only the folder as prefix
        last_part = url_parts[-1]
        if last_part.endswith('.json'):
            blob_prefix = "/".join(url_parts[2:-1]) + "/"  # Get only containing folder
        else:
            blob_prefix = "/".join(url_parts[2:]) + "/"    # already a folder
    else:
        raise ValueError(f"Unsupported blob URL format: {transcript_blob_url}")
    
    # Ensure prefix ends with / for proper folder listing
    if not blob_prefix.endswith("/"):
        blob_prefix += "/"
    
    return container_name, blob_prefix


# System prompt template for chat
SYSTEM_TEMPLATE = """The following is a friendly conversation between a Human (H) and an AI Assistant (AI) about a Video. There is no video provided to you but only a transcript of the video. Always remember the following points when having a conversation,

- The Video information is provided to you in the `Video Context` section below. You are to only answer based on the <video_context>...</video_context> and if the answer is not available respond with "I don't know, I'm sorry the requested information is not a part of the video".

- The video transcript is a non-overlapping second by second summary provided by a video transcriber. You are to answer a user's question based on the entire transcript and keep the user's conversation history in context when answering the question.

- Remember when a human asks about a video, always assume they are talking about the <video_context>...</video_context> transcript and respond appropriately. Your job depends on this.

- The user does not know that you (the assistant) has the video context. You should never reveal this information back to the user. Your job is to make them think that you analyzing the video live. It's your secret to never talk about <video_context>...</video_context>.

- Remember never reveal to the user about video context. Always pretend that you have access to the video.

- The video context is your biggest secret. Your job depends on this.

<video_context>
{video_context}
</video_context>
"""
