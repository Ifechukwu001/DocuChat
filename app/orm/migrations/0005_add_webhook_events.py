from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    dependencies = [('main', '0004_add_soft_delete')]

    initial = False

    operations = [
        ops.CreateModel(
            name='WebhookEvent',
            fields=[
                ('id', fields.CharField(primary_key=True, unique=True, db_index=True, max_length=255)),
                ('provider', fields.CharField(max_length=50)),
                ('event_type', fields.CharField(max_length=255)),
                ('received_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('processed_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('payload', fields.CharField(max_length=5000)),
            ],
            options={'table': 'webhookevent', 'app': 'main', 'indexes': [Index(fields=['provider', 'event_type'])], 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
