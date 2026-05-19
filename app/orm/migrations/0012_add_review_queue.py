from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from app.orm.enums.review_queue import ReviewPriority, ReviewStatus
from json import dumps, loads
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('main', '0011_add_ai_audit_log')]

    initial = False

    operations = [
        ops.CreateModel(
            name='ReviewQueue',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('message', fields.ForeignKeyField('main.Message', source_field='message_id', unique=True, db_constraint=True, to_field='id', on_delete=OnDelete.CASCADE)),
                ('document', fields.ForeignKeyField('main.Document', source_field='document_id', db_constraint=True, to_field='id', on_delete=OnDelete.CASCADE)),
                ('question', fields.TextField(unique=False)),
                ('generated_answer', fields.TextField(unique=False)),
                ('confidence', fields.FloatField()),
                ('sources', fields.JSONField(encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('reason', fields.CharField(null=True, max_length=255)),
                ('status', fields.CharEnumField(default=ReviewStatus.PENDING, description='PENDING: PENDING\nIN_REVIEW: IN_REVIEW\nAPPROVED: APPROVED\nREJECTED: REJECTED\nESCALATED: ESCALATED', enum_type=ReviewStatus, max_length=9)),
                ('priority', fields.CharEnumField(default=ReviewPriority.NORMAL, description='LOW: LOW\nNORMAL: NORMAL\nHIGH: HIGH\nURGENT: URGENT', enum_type=ReviewPriority, max_length=6)),
                ('reviewer', fields.ForeignKeyField('main.User', source_field='reviewed_by', null=True, db_constraint=True, to_field='id', on_delete=OnDelete.SET_NULL)),
                ('edited_answer', fields.TextField(null=True, unique=False)),
                ('reviewer_notes', fields.TextField(null=True, unique=False)),
                ('reviewed_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('escalated_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('sla_deadline', fields.DatetimeField(auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'reviewqueue', 'app': 'main', 'indexes': [Index(fields=['status', 'priority', 'created_at']), Index(fields=['reviewed_by']), Index(fields=['sla_deadline'])], 'pk_attr': 'id', 'table_description': 'HITL Review Queue Model.'},
            bases=['Model'],
        ),
    ]
