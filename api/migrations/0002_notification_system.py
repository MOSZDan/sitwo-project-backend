# api/migrations/0002_notification_system.py
# Generated manually for notification system

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoNotificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Tipo de Notificación',
                'verbose_name_plural': 'Tipos de Notificación',
                'db_table': 'tiponotificacion',
            },
        ),
        migrations.CreateModel(
            name='CanalNotificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(choices=[('email', 'Correo Electrónico'), ('push', 'Notificación Push'), ('sms', 'SMS'), ('whatsapp', 'WhatsApp')], max_length=50, unique=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Canal de Notificación',
                'verbose_name_plural': 'Canales de Notificación',
                'db_table': 'canalnotificacion',
            },
        ),
        migrations.CreateModel(
            name='DispositivoMovil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_fcm', models.TextField(unique=True)),
                ('plataforma', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS')], max_length=20)),
                ('modelo_dispositivo', models.CharField(blank=True, max_length=100, null=True)),
                ('version_app', models.CharField(blank=True, max_length=20, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('ultima_actividad', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(db_column='codusuario', on_delete=django.db.models.deletion.CASCADE, to='api.usuario')),
            ],
            options={
                'verbose_name': 'Dispositivo Móvil',
                'verbose_name_plural': 'Dispositivos Móviles',
                'db_table': 'dispositivomovil',
            },
        ),
        migrations.CreateModel(
            name='PreferenciaNotificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(db_column='codusuario', on_delete=django.db.models.deletion.CASCADE, to='api.usuario')),
                ('tipo_notificacion', models.ForeignKey(db_column='idtiponotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.tiponotificacion')),
                ('canal_notificacion', models.ForeignKey(db_column='idcanalnotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.canalnotificacion')),
            ],
            options={
                'verbose_name': 'Preferencia de Notificación',
                'verbose_name_plural': 'Preferencias de Notificación',
                'db_table': 'preferencianotificacion',
            },
        ),
        migrations.CreateModel(
            name='PlantillaNotificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('asunto_template', models.CharField(blank=True, max_length=200, null=True)),
                ('titulo_template', models.CharField(max_length=200)),
                ('mensaje_template', models.TextField()),
                ('variables_disponibles', models.JSONField(default=list, help_text='Lista de variables disponibles como {nombre}, {fecha}, etc.')),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('tipo_notificacion', models.ForeignKey(db_column='idtiponotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.tiponotificacion')),
                ('canal_notificacion', models.ForeignKey(db_column='idcanalnotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.canalnotificacion')),
            ],
            options={
                'verbose_name': 'Plantilla de Notificación',
                'verbose_name_plural': 'Plantillas de Notificación',
                'db_table': 'plantillanotificacion',
            },
        ),
        migrations.CreateModel(
            name='HistorialNotificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('mensaje', models.TextField()),
                ('datos_adicionales', models.JSONField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('enviado', 'Enviado'), ('entregado', 'Entregado'), ('leido', 'Leído'), ('error', 'Error')], default='pendiente', max_length=20)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_envio', models.DateTimeField(blank=True, null=True)),
                ('fecha_entrega', models.DateTimeField(blank=True, null=True)),
                ('fecha_lectura', models.DateTimeField(blank=True, null=True)),
                ('error_mensaje', models.TextField(blank=True, null=True)),
                ('intentos', models.IntegerField(default=0)),
                ('usuario', models.ForeignKey(db_column='codusuario', on_delete=django.db.models.deletion.CASCADE, to='api.usuario')),
                ('tipo_notificacion', models.ForeignKey(db_column='idtiponotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.tiponotificacion')),
                ('canal_notificacion', models.ForeignKey(db_column='idcanalnotificacion', on_delete=django.db.models.deletion.CASCADE, to='api.canalnotificacion')),
                ('dispositivo_movil', models.ForeignKey(blank=True, db_column='iddispositivomovil', null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.dispositivomovil')),
            ],
            options={
                'verbose_name': 'Historial de Notificación',
                'verbose_name_plural': 'Historial de Notificaciones',
                'db_table': 'historialnotificacion',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AddConstraint(
            model_name='preferencianotificacion',
            constraint=models.UniqueConstraint(fields=('usuario', 'tipo_notificacion', 'canal_notificacion'), name='unique_preferencia_usuario'),
        ),
        migrations.AddConstraint(
            model_name='plantillanotificacion',
            constraint=models.UniqueConstraint(fields=('tipo_notificacion', 'canal_notificacion'), name='unique_plantilla_tipo_canal'),
        ),
    ]