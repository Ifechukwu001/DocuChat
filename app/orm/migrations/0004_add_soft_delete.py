from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('main', '0003_add_rbac')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Conversation',
            name='latest_message',
            field=fields.ForeignKeyField('main.Message', source_field='latest_message_id', null=True, db_constraint=True, to_field='id', on_delete=OnDelete.SET_NULL),
        ),
        ops.AddField(
            model_name='Document',
            name='deleted_at',
            field=fields.DatetimeField(null=True, auto_now=False, auto_now_add=False),
        ),
        ops.AddField(
            model_name='Document',
            name='deleted_by',
            field=fields.UUIDField(null=True),
        ),
    ]
