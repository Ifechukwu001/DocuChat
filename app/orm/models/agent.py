# pyright: reportAssignmentType=false, reportUnknownVariableType=false
from uuid import UUID
from datetime import datetime

from tortoise import fields, models


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
