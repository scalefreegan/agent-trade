"""Conversation endpoints — multi-turn chat sessions with Claude."""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..conversation_manager import (
    ConversationBusy,
    ConversationNotFound,
    ConversationStatus,
    MessageRole,
    conversation_manager,
)
from ..dependencies import require_conversation_rate_limit, require_message_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    status: Literal["idle", "responding"]


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]
    status: Literal["idle", "responding"]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class CreateConversationRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class UpdateTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/conversations")
async def list_conversations() -> ConversationListResponse:
    """List all conversation sessions, most recent first."""
    convs = conversation_manager.list_conversations()
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=len(c.messages),
                status=c.status.value,
            )
            for c in convs
        ]
    )


@router.post(
    "/conversations",
    status_code=201,
    dependencies=[Depends(require_conversation_rate_limit)],
)
async def create_conversation(
    request: CreateConversationRequest,
) -> ConversationDetail:
    """Create a new conversation session."""
    conv = conversation_manager.create_conversation(title=request.title)
    return _conv_to_detail(conv)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> ConversationDetail:
    """Get a conversation with its full message history."""
    conv = conversation_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conv_to_detail(conv)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str):
    """Delete a conversation session. Returns 409 if the conversation is responding."""
    deleted, error = conversation_manager.delete_conversation(conversation_id)
    if error:
        raise HTTPException(status_code=409, detail=error)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.patch("/conversations/{conversation_id}")
async def update_conversation_title(
    conversation_id: str, request: UpdateTitleRequest
) -> ConversationDetail:
    """Update a conversation's title."""
    conv = conversation_manager.update_title(conversation_id, request.title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conv_to_detail(conv)


@router.post(
    "/conversations/{conversation_id}/messages",
    dependencies=[Depends(require_message_rate_limit)],
)
async def send_message(
    conversation_id: str, request: SendMessageRequest
) -> MessageResponse:
    """Send a user message to a conversation and trigger an assistant response.

    The assistant response is generated asynchronously. Poll the conversation
    detail endpoint to get the response once the status returns to 'idle'.
    """
    try:
        user_msg = conversation_manager.send_message(conversation_id, request.content)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except ConversationBusy:
        raise HTTPException(status_code=409, detail="Conversation is already processing a response")

    return MessageResponse(
        id=user_msg.id,
        role=user_msg.role.value,
        content=user_msg.content,
        timestamp=user_msg.timestamp,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _conv_to_detail(conv) -> ConversationDetail:
    """Convert a Conversation object to ConversationDetail response."""
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        status=conv.status.value,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role.value,
                content=m.content,
                timestamp=m.timestamp,
            )
            for m in conv.messages
        ],
    )
