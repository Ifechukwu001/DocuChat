# pyright: reportAssignmentType=false, reportUnknownVariableType=false
from datetime import datetime

from tortoise import fields, models


class WebhookEvent(models.Model):
    id: str = fields.CharField(primary_key=True, max_length=255)
    provider: str = fields.CharField(max_length=50)
    event_type: str = fields.CharField(max_length=255)
    received_at: datetime = fields.DatetimeField(auto_now_add=True)
    processed_at: datetime | None = fields.DatetimeField(null=True)
    payload: str = fields.CharField(max_length=5000)

    class Meta(models.Model.Meta):
        indexes = (("provider", "event_type"),)
