from tortoise import migrations
from tortoise.migrations import operations as ops

class Migration(migrations.Migration):
    dependencies = [('main', '0007_add_vector_column')]

    initial = False

    operations = [
        ops.RunSQL(
            sql="CREATE INDEX hsnw_idx ON Chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);",
            reverse_sql="DROP INDEX IF EXISTS hsnw_idx;"
            # m = 16: each node connects to 16 neighbors (higher = more accurate, more memory)
            # ef_construction = 64: search quality during build (higher = better index, slower build)
        )
    ]
