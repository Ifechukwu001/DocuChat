from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise_vector.field import VectorField

class Migration(migrations.Migration):
    dependencies = [('main', '0008_add_hsnw_index')]

    initial = False

    operations = [
        ops.AlterField(
            model_name='Chunk',
            name='embedding',
            field=VectorField(vector_size=1536,null=True),
        ),
    ]
