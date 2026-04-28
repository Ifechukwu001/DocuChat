from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise_vector.field import VectorField

class Migration(migrations.Migration):
    dependencies = [('main', '0006_enable_pgvector')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Chunk',
            name='embedding',
            field=VectorField(vector_size=1536),
        ),
    ]
