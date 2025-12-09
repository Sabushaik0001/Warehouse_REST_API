"""
Unit Tests for Chat Endpoint

Tests for:
- POST /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat
  AI-powered video chat with AWS Bedrock integration
"""

import pytest
from unittest.mock import patch, MagicMock
import uuid


@pytest.mark.unit
class TestChatWithVideo:
    """Test suite for POST /api/v1/warehouses/{warehouse_id}/cameras/{cam_id}/chunks/{chunk_id}/chat endpoint"""
    
    def test_chat_success_first_message(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request,
        mock_aws_bedrock_response
    ):
        """Test successful chat with first message (no conversation history)"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        # Mock Azure Blob and AWS services
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"timestamp": "00:00:05", "text": "Vehicle entering"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Video context data"):
                    with patch('app.services.aws_service.bedrock_client.converse', return_value=mock_aws_bedrock_response):
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=sample_chat_request
                        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversation" in data
        assert len(data["conversation"]) == 2  # user + assistant
        assert data["conversation"][0]["role"] == "user"
        assert data["conversation"][1]["role"] == "assistant"
        assert "chatTransactionId" in data
        assert "chatLastTime" in data
        assert data["modelId"] == sample_chat_request["modelId"]
    
    def test_chat_with_conversation_history(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        mock_aws_bedrock_response
    ):
        """Test chat with existing conversation history"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        # Request with conversation history
        request_with_history = {
            "UserQuery": "What else can you tell me?",
            "modelId": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.7,
                "topP": 0.9
            },
            "conversation": [
                {
                    "role": "user",
                    "content": [{"text": "How many vehicles?"}]
                },
                {
                    "role": "assistant",
                    "content": [{"text": "I saw 3 vehicles."}]
                }
            ],
            "chatTransactionId": "test-transaction-123"
        }
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"timestamp": "00:00:05"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Video context"):
                    with patch('app.services.aws_service.bedrock_client.converse', return_value=mock_aws_bedrock_response):
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=request_with_history
                        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 4 messages: 2 from history + 1 user + 1 assistant
        assert len(data["conversation"]) == 4
        assert data["chatTransactionId"] == "test-transaction-123"
    
    def test_chat_chunk_not_found(
        self,
        test_client,
        mock_get_connection,
        sample_chat_request
    ):
        """Test response when chunk doesn't exist"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = None
        
        response = test_client.post(
            "/api/v1/warehouses/WH999/cameras/CAM999/chunks/invalid_chunk/chat",
            json=sample_chat_request
        )
        
        assert response.status_code == 404
        assert "Chunk not found" in response.json()["detail"]
    
    def test_chat_no_transcript_url(
        self,
        test_client,
        mock_get_connection,
        sample_chat_request
    ):
        """Test response when chunk has no transcript URL"""
        mock_conn, mock_cursor = mock_get_connection
        
        # Chunk row with NULL transcript URL
        chunk_row_no_transcript = (
            "chunk_2025-11-19_10-00-00", "WH001", "CAM001",
            "https://example.com/chunks/chunk1.mp4",
            None,  # NULL transcript URL
            None, None
        )
        mock_cursor.fetchone.return_value = chunk_row_no_transcript
        
        response = test_client.post(
            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
            json=sample_chat_request
        )
        
        assert response.status_code == 400
        assert "No transcript URL configured" in response.json()["detail"]
    
    def test_chat_no_transcript_files_found(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request
    ):
        """Test response when no transcript files exist in blob storage"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=[]):
            response = test_client.post(
                "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                json=sample_chat_request
            )
        
        assert response.status_code == 404
        assert "No transcript files found" in response.json()["detail"]
    
    def test_chat_transcript_merge_failure(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request
    ):
        """Test handling of transcript merge errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', side_effect=Exception("Blob storage error")):
                response = test_client.post(
                    "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                    json=sample_chat_request
                )
        
        assert response.status_code == 500
    
    def test_chat_context_build_failure(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request
    ):
        """Test response when video context build fails"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"data": "test"}]):
                with patch('app.services.transcript_service.build_video_context', return_value=None):
                    response = test_client.post(
                        "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                        json=sample_chat_request
                    )
        
        assert response.status_code == 500
        assert "Failed to build video context" in response.json()["detail"]
    
    def test_chat_aws_bedrock_error(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request
    ):
        """Test handling of AWS Bedrock API errors"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"data": "test"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Context"):
                    with patch('app.services.aws_service.bedrock_client.converse', side_effect=Exception("Bedrock API error")):
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=sample_chat_request
                        )
        
        assert response.status_code == 500
    
    def test_chat_empty_bedrock_response(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request
    ):
        """Test handling of empty Bedrock response"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        # Empty response from Bedrock
        empty_response = {}
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"data": "test"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Context"):
                    with patch('app.services.aws_service.bedrock_client.converse', return_value=empty_response):
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=sample_chat_request
                        )
        
        assert response.status_code == 500
        assert "No response from AI model" in response.json()["detail"]
    
    def test_chat_invalid_request_payload(self, test_client):
        """Test validation of request payload"""
        invalid_request = {
            "UserQuery": "",  # Empty query
            "modelId": "anthropic.claude-3-5-haiku-20241022-v1:0"
            # Missing inferenceConfig
        }
        
        response = test_client.post(
            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_test/chat",
            json=invalid_request
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_custom_inference_config(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        mock_aws_bedrock_response
    ):
        """Test chat with custom inference configuration"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        custom_config_request = {
            "UserQuery": "Test query",
            "modelId": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.5,
                "topP": 0.8
            },
            "conversation": [],
            "chatTransactionId": None
        }
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"data": "test"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Context"):
                    with patch('app.services.aws_service.bedrock_client.converse', return_value=mock_aws_bedrock_response) as mock_bedrock:
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=custom_config_request
                        )
                        
                        # Verify custom config was passed to Bedrock
                        call_args = mock_bedrock.call_args
                        assert call_args[1]["inferenceConfig"]["maxTokens"] == 4096
                        assert call_args[1]["inferenceConfig"]["temperature"] == 0.5
                        assert call_args[1]["inferenceConfig"]["topP"] == 0.8
        
        assert response.status_code == 200
    
    def test_chat_transaction_id_generation(
        self,
        test_client,
        mock_get_connection,
        sample_chunk_rows,
        sample_chat_request,
        mock_aws_bedrock_response
    ):
        """Test automatic generation of transaction ID when not provided"""
        mock_conn, mock_cursor = mock_get_connection
        mock_cursor.fetchone.return_value = sample_chunk_rows[0]
        
        with patch('app.services.transcript_service.list_transcript_files', return_value=['transcript1.json']):
            with patch('app.services.transcript_service.merge_transcripts', return_value=[{"data": "test"}]):
                with patch('app.services.transcript_service.build_video_context', return_value="Context"):
                    with patch('app.services.aws_service.bedrock_client.converse', return_value=mock_aws_bedrock_response):
                        response = test_client.post(
                            "/api/v1/warehouses/WH001/cameras/CAM001/chunks/chunk_2025-11-19_10-00-00/chat",
                            json=sample_chat_request
                        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have auto-generated transaction ID
        assert data["chatTransactionId"] is not None
        assert len(data["chatTransactionId"]) > 0
