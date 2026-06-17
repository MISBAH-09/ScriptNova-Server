from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ScriptNova', '0006_blog_humanized_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='plan',
            field=models.CharField(default='free', max_length=20),
        ),
        migrations.AddField(
            model_name='user',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='stripe_subscription_status',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
