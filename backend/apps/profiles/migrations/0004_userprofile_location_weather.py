from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0003_userprofile_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="city",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="location_source",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="weather_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="weather_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
