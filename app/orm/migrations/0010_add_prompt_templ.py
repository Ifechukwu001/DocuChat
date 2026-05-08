from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('main', '0009_alter_vector_column_nullable')]

    initial = False

    operations = [
        ops.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('task_type', fields.CharField(max_length=50)),
                ('version', fields.CharField(max_length=20)),
                ('name', fields.CharField(max_length=100)),
                ('content', fields.TextField(unique=False)),
                ('is_active', fields.BooleanField(default=False)),
                ('metadata', fields.CharField(null=True, max_length=500)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'prompttemplate', 'app': 'main', 'unique_together': (('task_type', 'version'),), 'indexes': [Index(fields=['task_type', 'is_active'])], 'pk_attr': 'id', 'table_description': 'Prompt Template Model.'},
            bases=['Model'],
        ),
        ops.AlterModelOptions(
            name='WebhookEvent',
            options={'table': 'webhookevent', 'app': 'main', 'indexes': [Index(fields=['provider', 'event_type'])], 'pk_attr': 'id', 'table_description': 'Webhook Event Model.'},
        ),
    ]
