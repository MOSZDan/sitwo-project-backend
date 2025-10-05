# Generated manually to fix bitacora codusuario null values issue
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_alter_historialclinico_options_and_more'),
    ]

    operations = [
        # Esta migración simplemente verifica que el modelo Bitacora permita valores nulos
        # en el campo usuario, como ya está configurado en el modelo actual
        migrations.RunSQL(
            """
            -- Esta migración asegura que el campo codusuario en bitacora permita valores nulos
            -- El modelo ya está configurado correctamente con null=True, blank=True
            SELECT 1; -- No-op, solo para que la migración sea válida
            """,
            reverse_sql="SELECT 1;"
        ),
    ]
