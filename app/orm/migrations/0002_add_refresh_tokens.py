from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('main', '0001_initial')]

    initial = False

    operations = [
        ops.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('main.User', source_field='user_id', db_constraint=True, to_field='id', related_name='refresh_tokens', on_delete=OnDelete.CASCADE)),
                ('token', fields.CharField(unique=True, max_length=255)),
                ('expires_at', fields.DatetimeField(auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'refreshtoken', 'app': 'main', 'indexes': [Index(fields=['expires_at'])], 'pk_attr': 'id', 'table_description': 'Refresh Token Model.'},
            bases=['Model'],
        ),
    ]
