# Generated migration for Stripe integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_add_empresa_to_catalog_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='stripe_customer_id',
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text="ID del cliente en Stripe"
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='stripe_subscription_id',
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text="ID de la suscripción en Stripe"
            ),
        ),
    ]