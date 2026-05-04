from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise_vector.field import VectorField

class Migration(migrations.Migration):
    dependencies = [('main', '0009_alter_vector_column_nullable')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Chunk',
            name='embedding',
            field=VectorField(vector_size=768, null=True),
        ),
    ]
