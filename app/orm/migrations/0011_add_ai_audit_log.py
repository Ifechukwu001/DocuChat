from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('main', '0010_add_prompt_templ')]

    initial = False

    operations = [
        ops.CreateModel(
            name='AIAuditLog',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user_id', fields.UUIDField()),
                ('correlation_id', fields.CharField(max_length=255)),
                ('task_type', fields.CharField(max_length=50)),
                ('model', fields.CharField(max_length=100)),
                ('prompt_version', fields.CharField(max_length=50)),
                ('input_tokens', fields.IntField()),
                ('output_tokens', fields.IntField()),
                ('cost_usd', fields.FloatField()),
                ('latency_secs', fields.FloatField()),
                ('fallback_used', fields.BooleanField(default=False)),
                ('input_data', fields.TextField(null=True, unique=False)),
                ('output_data', fields.TextField(null=True, unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'aiauditlog', 'app': 'main', 'indexes': [Index(fields=['user_id', 'created_at']), Index(fields=['task_type', 'created_at']), Index(fields=['model', 'created_at'])], 'pk_attr': 'id', 'table_description': 'AI Audit Log Model.'},
            bases=['Model'],
        ),
    ]
