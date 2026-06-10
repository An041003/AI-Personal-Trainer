from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0004_userprofile_location_weather"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="dashboard_greeting_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="dashboard_greeting_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
