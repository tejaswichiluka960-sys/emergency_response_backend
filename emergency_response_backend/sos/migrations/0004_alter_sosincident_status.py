from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('sos', '0003_incidenthistory')]

    operations = [
        migrations.AlterField(
            model_name='sosincident',
            name='status',
            field=models.CharField(
                choices=[
                    ('OPEN', 'Open'),
                    ('NOTIFICATIONS_SENT', 'Notifications Sent'),
                    ('RESPONSE_RECEIVED', 'Response Received'),
                    ('ACTIVE_RESPONSE', 'Active Response'),
                    ('RESOLVED', 'Resolved'),
                    ('CANCELLED', 'Cancelled'),
                    ('ESCALATED', 'Escalated'),
                    ('CLOSED', 'Closed'),
                ],
                default='OPEN',
                max_length=30,
            ),
        ),
    ]
