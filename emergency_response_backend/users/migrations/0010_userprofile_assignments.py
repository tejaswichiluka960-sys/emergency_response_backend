from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_userprofile_role_manual"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="society_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="flat_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
