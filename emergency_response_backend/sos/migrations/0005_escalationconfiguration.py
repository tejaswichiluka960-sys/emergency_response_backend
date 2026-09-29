from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('sos', '0004_alter_sosincident_status')]

    operations = [
        migrations.CreateModel(
            name='EscalationConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response_timeout_seconds', models.PositiveIntegerField(default=60)),
                ('primary_guardian_enabled', models.BooleanField(default=True)),
                ('secondary_guardian_enabled', models.BooleanField(default=True)),
                ('emergency_contact_enabled', models.BooleanField(default=True)),
                ('security_enabled', models.BooleanField(default=True)),
                ('volunteer_enabled', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Escalation configuration'},
        ),
    ]
