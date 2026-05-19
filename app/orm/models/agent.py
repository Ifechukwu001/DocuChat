# pyright: reportAssignmentType=false, reportUnknownVariableType=false
from uuid import UUID
from datetime import datetime

from tortoise import fields, models

from app.orm.enums.review_queue import ReviewStatus, ReviewPriority

from .users import User
from .documents import Document
from .conversations import Message


class PromptTemplate(models.Model):
    """Prompt Template Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    task_type: str = fields.CharField(max_length=50)  # 'chat', 'agent', 'summary'
    version: str = fields.CharField(max_length=20)  # 'v1', 'v2', 'v3'
    name: str = fields.CharField(max_length=100)  # Human-readable name
    content: str = fields.TextField()  # The actual prompt text
    is_active: bool = fields.BooleanField(default=False)
    metadata: str | None = fields.CharField(  #  JSON: notes, author, changelog
        max_length=500, null=True
    )
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """Prompt Template Meta."""

        indexes = (("task_type", "is_active"),)
        unique_together = (("task_type", "version"),)


class AIAuditLog(models.Model):
    """AI Audit Log Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    user_id: UUID = fields.UUIDField()
    correlation_id: str = fields.CharField(max_length=255)
    task_type: str = fields.CharField(max_length=50)
    model: str = fields.CharField(max_length=100)
    prompt_version: str = fields.CharField(max_length=50)
    input_tokens: int = fields.IntField()
    output_tokens: int = fields.IntField()
    cost_usd: float = fields.FloatField()
    latency_secs: float = fields.FloatField()
    fallback_used: bool = fields.BooleanField(default=False)
    # Store input/output as text, NOT in metadata JSON
    # This allows searching and analysis
    input_data: str = fields.TextField(
        null=True
    )  # First 500 chars of the prompt (not full PII)
    output_data: str = fields.TextField(null=True)  # First 500 chars of the response
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """AI Audit Log Meta."""

        indexes = (
            ("user_id", "created_at"),
            ("task_type", "created_at"),
            ("model", "created_at"),
        )


class ReviewQueue(models.Model):
    """HITL Review Queue Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    message: fields.ForeignKeyRelation[Message] = fields.ForeignKeyField(
        "main.Message", unique=True
    )
    document: fields.ForeignKeyRelation[Document] = fields.ForeignKeyField(
        "main.Document"
    )
    question: str = fields.TextField()
    generated_answer: str = fields.TextField()
    confidence: float = fields.FloatField()
    sources = fields.JSONField()
    reason: str | None = fields.CharField(max_length=255, null=True)
    status: ReviewStatus = fields.CharEnumField(
        ReviewStatus, default=ReviewStatus.PENDING
    )
    priority: ReviewPriority = fields.CharEnumField(
        ReviewPriority, default=ReviewPriority.NORMAL
    )
    reviewer: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "main.User", source_field="reviewed_by", on_delete=fields.SET_NULL, null=True
    )
    edited_answer: str | None = fields.TextField(null=True)
    reviewer_notes: str | None = fields.TextField(null=True)
    reviewed_at: datetime | None = fields.DatetimeField(null=True)
    escalated_at: datetime | None = fields.DatetimeField(null=True)
    sla_deadline: datetime = fields.DatetimeField()
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    # Annotation
    message_id: UUID
    reviewed_by: UUID | None

    class Meta(models.Model.Meta):
        """Review Queue Meta."""

        indexes = (
            ("status", "priority", "created_at"),
            ("reviewed_by",),
            ("sla_deadline",),
        )
