from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('sos', '0006_sosnotification_is_read'),
    ]

    operations = [
        migrations.CreateModel(
            name='IncidentMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(choices=[('TEXT', 'Text'), ('VOICE', 'Voice')], default='TEXT', max_length=10)),
                ('message', models.TextField(blank=True)),
                ('audio_file', models.FileField(blank=True, null=True, upload_to='incident_voice_messages/%Y/%m/%d/')),
                ('duration_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('incident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='sos.sosincident')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incident_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
    ]
