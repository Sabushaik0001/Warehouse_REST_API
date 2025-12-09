"""
Chat router - AI-powered video chat functionality
"""

from fastapi import APIRouter, HTTPException, Path, Body
from app.core.database import get_connection
from app.models.chat import ChatRequest, ChatResponse, MessageContent, ConversationMessage
from app.services.aws_service import bedrock_client
from app.services.transcript_service import (
    list_transcript_files,
    merge_transcripts,
    build_video_context,
    parse_blob_url,
    SYSTEM_TEMPLATE
)
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/warehouses", tags=["chat"])


@router.post(
    "/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat",
    response_model=ChatResponse,
    summary="Chat with AI about video chunk",
    description="Ask questions about a specific video chunk using AI assistant"
)
async def chat_with_video(
    warehouse_id: str = Path(..., description="Warehouse ID (e.g., WH001)"),
    cam_id: str = Path(..., description="Camera ID"),
    chunk_id: str = Path(..., description="Chunk ID (e.g., chunk_2025-01-15_10-00-00)"),
    request: ChatRequest = Body(...)
):
    """
    Chat endpoint for asking questions about video content
    
    This endpoint:
    1. Fetches chunk transcript URL from database
    2. Retrieves and merges video transcripts from Azure Blob Storage
    3. Builds context from transcript
    4. Sends query to AWS Bedrock AI with conversation history
    5. Returns AI response with updated conversation
    """
    
    try:
        logger.info(f"Chat request for warehouse={warehouse_id}, camera={cam_id}, chunk={chunk_id}")
        
        # Step 1: Get chunk transcript URL from database
        conn = get_connection()
        cur = conn.cursor()
        
        chunk_query = """
            SELECT 
                chunk_id,
                warehouse_id,
                cam_id,
                chunk_blob_url,
                transcripts_url,
                date,
                time
            FROM public.wh_chunks
            WHERE warehouse_id = %s AND cam_id = %s AND chunk_id = %s
        """
        cur.execute(chunk_query, (warehouse_id, cam_id, chunk_id))
        chunk_row = cur.fetchone()
        
        if not chunk_row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Chunk not found: warehouse_id={warehouse_id}, cam_id={cam_id}, chunk_id={chunk_id}"
            )
        
        # Use hardcoded URL for testing - replace with chunk_row[4] in production
        transcript_blob_url = "https://spectradevdev.blob.core.windows.net/cache-0e83775c98f1d6627efbe49f1ca0ba9b-eastus/2025-08-26/loopcam1/10028814-d9e1-4c85-8a7d-74e034381b4d/chunks/ts_10028814-d9e1-4c85-8a7d-74e034381b4d_chunk_start-0-end-30_file.json"
        
        if not transcript_blob_url:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"No transcript URL configured for chunk {chunk_id}"
            )
        
        cur.close()
        conn.close()
        
        # Step 2: Parse Blob URL
        container_name, blob_prefix = parse_blob_url(transcript_blob_url)
        logger.info(f"Looking for transcripts in container: {container_name}, prefix: {blob_prefix}")
        
        # Step 3: List and merge transcript files
        transcript_blobs = list_transcript_files(container_name, blob_prefix)
        
        if not transcript_blobs:
            raise HTTPException(
                status_code=404,
                detail=f"No transcript files found for chunk_id={chunk_id}"
            )
        
        transcript_data = merge_transcripts(container_name, transcript_blobs)
        logger.info(f"Merged {len(transcript_blobs)} transcript files")
        
        # Step 4: Build video context
        video_context = build_video_context(transcript_data)
        
        if not video_context:
            raise HTTPException(
                status_code=500,
                detail="Failed to build video context from transcripts"
            )
        
        # Step 5: Prepare system prompt and messages
        system_prompt = SYSTEM_TEMPLATE.replace("{video_context}", video_context)
        system_list = [{"text": system_prompt}]
        
        # Build message list with conversation history
        message_list = []
        if request.conversation:
            message_list = [
                {
                    "role": msg.role,
                    "content": [{"text": c.text} for c in msg.content]
                }
                for msg in request.conversation
            ]
        
        # Add current user query
        message_list.append({
            "role": "user",
            "content": [{"text": request.UserQuery}]
        })
        
        # Step 6: Call AWS Bedrock
        logger.info(f"Calling Bedrock model: {request.modelId}")
        
        inference_config = {
            "maxTokens": request.inferenceConfig.maxTokens,
            "temperature": request.inferenceConfig.temperature,
            "topP": request.inferenceConfig.topP
        }
        
        # Use inference profile ARN
        inference_profile_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
        
        bedrock_response = bedrock_client.converse(
            modelId=inference_profile_arn,
            messages=message_list,
            system=system_list,
            inferenceConfig=inference_config
        )
        
        # Step 7: Extract assistant response
        if not (bedrock_response and 'output' in bedrock_response and 
                'message' in bedrock_response['output']):
            raise HTTPException(
                status_code=500,
                detail="No response from AI model"
            )
        
        assistant_text = bedrock_response['output']['message']['content'][0]['text']
        logger.info(f"Assistant response received: {len(assistant_text)} characters")
        
        # Step 8: Add assistant response to conversation
        message_list.append({
            "role": "assistant",
            "content": [{"text": assistant_text}]
        })
        
        # Step 9: Build response
        chat_transaction_id = request.chatTransactionId or str(uuid.uuid4().hex)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert back to Pydantic models for response
        conversation_response = [
            ConversationMessage(
                role=msg["role"],
                content=[MessageContent(text=c["text"]) for c in msg["content"]]
            )
            for msg in message_list
        ]
        
        return ChatResponse(
            conversation=conversation_response,
            chatLastTime=current_time,
            chatTransactionId=chat_transaction_id,
            modelId=request.modelId,
            inferenceConfig=request.inferenceConfig
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
