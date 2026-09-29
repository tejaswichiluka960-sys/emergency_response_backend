from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_userprofile_assignments"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_available",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="availability_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="location_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
