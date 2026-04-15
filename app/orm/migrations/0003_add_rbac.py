from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('main', '0002_add_refresh_tokens')]

    initial = False

    operations = [
        ops.CreateModel(
            name='Permission',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('name', fields.CharField(unique=True, max_length=50)),
                ('description', fields.CharField(null=True, max_length=255)),
                ('resource', fields.CharField(null=True, max_length=255)),
                ('action', fields.CharField(null=True, max_length=50)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'permission', 'app': 'main', 'unique_together': (('resource', 'action'),), 'pk_attr': 'id', 'table_description': 'Permission Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Role',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('name', fields.CharField(unique=True, max_length=50)),
                ('description', fields.CharField(null=True, max_length=255)),
                ('is_default', fields.BooleanField(default=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'role', 'app': 'main', 'pk_attr': 'id', 'table_description': 'Role Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='RolePermission',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('role', fields.ForeignKeyField('main.Role', source_field='role_id', db_constraint=True, to_field='id', related_name='permissions', on_delete=OnDelete.CASCADE)),
                ('permission', fields.ForeignKeyField('main.Permission', source_field='permission_id', db_constraint=True, to_field='id', related_name='roles', on_delete=OnDelete.CASCADE)),
            ],
            options={'table': 'rolepermission', 'app': 'main', 'unique_together': (('role', 'permission'),), 'pk_attr': 'id', 'table_description': 'Role Permission Model.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='UserRole',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('main.User', source_field='user_id', db_constraint=True, to_field='id', related_name='roles', on_delete=OnDelete.CASCADE)),
                ('role', fields.ForeignKeyField('main.Role', source_field='role_id', db_constraint=True, to_field='id', related_name='users', on_delete=OnDelete.CASCADE)),
                ('assigned_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('assigned_by', fields.UUIDField(null=True)),
            ],
            options={'table': 'userrole', 'app': 'main', 'unique_together': (('user', 'role'),), 'pk_attr': 'id', 'table_description': 'User Role Model.'},
            bases=['Model'],
        ),
    ]
