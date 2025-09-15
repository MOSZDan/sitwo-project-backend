# api/migrations/0002_add_notification_preferences.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='notificaciones_email',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='notificaciones_push',
            field=models.BooleanField(default=False),
        ),
    ]