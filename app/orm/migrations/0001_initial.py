from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='AITrace',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('trace_id', fields.CharField(unique=True, max_length=255)),
                ('user_id', fields.UUIDField(null=True)),
                ('operation', fields.CharField(max_length=100)),
                ('data', fields.TextField(null=True, unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'aitrace', 'app': 'main', 'indexes': [Index(fields=['user_id', 'operation'])], 'pk_attr': 'id', 'table_description': 'AI Trace Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('email', fields.CharField(unique=True, max_length=255)),
                ('password_hash', fields.CharField(max_length=255)),
                ('tier', fields.CharField(default='free', max_length=50)),
                ('tokens_used', fields.IntField(default=0)),
                ('token_limit', fields.IntField(default=10000)),
                ('is_active', fields.BooleanField(default=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'user', 'app': 'main', 'pk_attr': 'id', 'table_description': 'User Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Conversation',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('main.User', source_field='user_id', db_constraint=True, to_field='id', related_name='conversations', on_delete=OnDelete.CASCADE)),
                ('title', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'conversation', 'app': 'main', 'pk_attr': 'id', 'table_description': 'Conversation Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Document',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('main.User', source_field='user_id', db_constraint=True, to_field='id', related_name='documents', on_delete=OnDelete.CASCADE)),
                ('title', fields.CharField(max_length=255)),
                ('filename', fields.CharField(max_length=255)),
                ('content', fields.TextField(unique=False)),
                ('mime_type', fields.CharField(null=True, max_length=100)),
                ('file_size_bytes', fields.IntField(null=True)),
                ('chunk_count', fields.IntField(default=0)),
                ('status', fields.CharField(default='pending', max_length=50)),
                ('error', fields.TextField(null=True, unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'document', 'app': 'main', 'indexes': [Index(fields=['status'])], 'pk_attr': 'id', 'table_description': 'Document Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Chunk',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('document', fields.ForeignKeyField('main.Document', source_field='document_id', db_constraint=True, to_field='id', related_name='chunks', on_delete=OnDelete.CASCADE)),
                ('index', fields.IntField()),
                ('content', fields.TextField(unique=False)),
                ('token_count', fields.IntField()),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'chunk', 'app': 'main', 'unique_together': (('document', 'index'),), 'pk_attr': 'id', 'table_description': 'Chunk Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Message',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('conversation', fields.ForeignKeyField('main.Conversation', source_field='conversation_id', db_constraint=True, to_field='id', related_name='messages', on_delete=OnDelete.CASCADE)),
                ('document', fields.ForeignKeyField('main.Document', source_field='document_id', null=True, db_constraint=True, to_field='id', related_name='messages', on_delete=OnDelete.SET_NULL)),
                ('role', fields.CharField(max_length=50)),
                ('content', fields.TextField(unique=False)),
                ('sources', fields.TextField(null=True, unique=False)),
                ('confidence', fields.CharField(null=True, max_length=50)),
                ('prompt_tokens', fields.IntField(null=True)),
                ('completion_tokens', fields.IntField(null=True)),
                ('cost_usd', fields.FloatField(null=True)),
                ('latency_ms', fields.IntField(null=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'message', 'app': 'main', 'pk_attr': 'id', 'table_description': 'Message Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='UsageLog',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('main.User', source_field='user_id', db_constraint=True, to_field='id', related_name='usage_logs', on_delete=OnDelete.CASCADE)),
                ('action', fields.CharField(max_length=50)),
                ('tokens', fields.IntField()),
                ('cost_usd', fields.FloatField()),
                ('metadata', fields.TextField(null=True, unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'usagelog', 'app': 'main', 'indexes': [Index(fields=['action', 'created_at'])], 'pk_attr': 'id', 'table_description': 'Usage Log Model.'},
            bases=['Model'],
        ),
    ]
