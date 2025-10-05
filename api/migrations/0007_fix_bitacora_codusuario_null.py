# Generated manually to safely handle Vista model removal
from django.db import migrations


def remove_vista_tables_safely(apps, schema_editor):
    """Remove Vista tables only if they exist"""
    from django.db import connection

    with connection.cursor() as cursor:
        try:
            # Check and drop vista_roles_permitidos table if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'vista_roles_permitidos'
                );
            """)
            if cursor.fetchone()[0]:
                cursor.execute('DROP TABLE IF EXISTS vista_roles_permitidos CASCADE;')
                print("✅ Tabla vista_roles_permitidos eliminada")

            # Check and drop vista table if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'vista'
                );
            """)
            if cursor.fetchone()[0]:
                cursor.execute('DROP TABLE IF EXISTS vista CASCADE;')
                print("✅ Tabla vista eliminada")

            print("✅ Limpieza de tablas Vista completada")
        except Exception as e:
            print(f"⚠️ Error limpiando tablas Vista: {e}")
            # No fallar la migración por esto


def reverse_remove_vista_tables(apps, schema_editor):
    """Reverse operation - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_alter_historialclinico_options_and_more'),
    ]

    operations = [
        # Limpiar tablas Vista de forma segura
        migrations.RunPython(
            remove_vista_tables_safely,
            reverse_remove_vista_tables,
        ),

        # Esta parte maneja bitácora
        migrations.RunSQL(
            """
            -- Asegurar que el campo codusuario en bitacora permita valores nulos
            ALTER TABLE bitacora ALTER COLUMN codusuario DROP NOT NULL;
            """,
            reverse_sql="""
            -- En reverse, no hacer nada específico
            SELECT 1;
            """
        ),
    ]
