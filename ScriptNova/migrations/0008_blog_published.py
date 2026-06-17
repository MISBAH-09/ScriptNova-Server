from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ScriptNova', '0007_user_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='published',
            field=models.BooleanField(default=False),
        ),
    ]
