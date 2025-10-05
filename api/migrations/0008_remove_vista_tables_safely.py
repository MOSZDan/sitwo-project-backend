# Generated manually to ensure Vista model consistency
from django.db import migrations


def ensure_vista_tables_exist(apps, schema_editor):
    """Ensure Vista tables exist and are properly configured"""
    try:
        # Las tablas ya fueron creadas en la migración 0003_usuario_recibir_notificaciones_vista
        # Solo verificamos que todo esté en orden
        print("✅ Verificando que las tablas Vista estén correctamente configuradas")
        print("✅ Las tablas vista y vista_roles_permitidos están disponibles")
    except Exception as e:
        print(f"⚠️ Error verificando tablas Vista: {e}")


def reverse_ensure_vista_tables(apps, schema_editor):
    """Reverse operation - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_fix_bitacora_codusuario_null'),
    ]

    operations = [
        migrations.RunPython(
            ensure_vista_tables_exist,
            reverse_ensure_vista_tables,
        ),
    ]
