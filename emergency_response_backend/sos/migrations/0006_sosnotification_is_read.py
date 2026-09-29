from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sos', '0005_escalationconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='sosnotification',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
