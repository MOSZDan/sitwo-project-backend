"""Set fecha field to NOT NULL after backfilling existing data

This migration:
1. First fills NULL values in `fecha` using `updated_at` or current time
2. Then sets the field to NOT NULL
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_add_fecha_field'),
    ]

    operations = [
        # First, backfill any NULL fecha values
        migrations.RunSQL(
            # Fill NULL valores in fecha before setting NOT NULL constraint
            sql="""
                UPDATE historialclinico 
                SET fecha = COALESCE(updated_at, NOW()) 
                WHERE fecha IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        
        # Then set the field to NOT NULL
        migrations.AlterField(
            model_name='historialclinico',
            name='fecha',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
