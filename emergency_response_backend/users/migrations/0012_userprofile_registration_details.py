from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_userprofile_availability_timestamps"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="society_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="flat_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
