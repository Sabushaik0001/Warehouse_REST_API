"""
Pydantic models for Chat API requests and responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class MessageContent(BaseModel):
    text: str


class ConversationMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: List[MessageContent]


class InferenceConfig(BaseModel):
    maxTokens: Optional[int] = Field(1000, description="Maximum tokens in response")
    temperature: Optional[float] = Field(0.7, description="Temperature for response randomness")
    topP: Optional[float] = Field(0.9, description="Top P sampling parameter")


class ChatRequest(BaseModel):
    UserQuery: str = Field(..., description="User's question about the video")
    modelId: str = Field("anthropic.claude-3-5-haiku-20241022-v1:0", description="Bedrock model ID")
    conversation: Optional[List[ConversationMessage]] = Field([], description="Previous conversation history")
    inferenceConfig: Optional[InferenceConfig] = Field(default_factory=InferenceConfig)
    chatTransactionId: Optional[str] = Field(None, description="Transaction ID for tracking")


class ChatResponse(BaseModel):
    conversation: List[ConversationMessage]
    chatLastTime: str
    chatTransactionId: str
    modelId: str
    inferenceConfig: InferenceConfig
