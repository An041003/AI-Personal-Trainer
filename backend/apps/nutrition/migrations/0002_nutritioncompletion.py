from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0004_user_owned_row_level_security"),
        ("nutrition", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NutritionCompletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nutrition_date", models.DateField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="nutrition_completions",
                        to="common.plan",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nutrition_completions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "nutrition_completion",
                "ordering": ["-nutrition_date"],
            },
        ),
        migrations.AddIndex(
            model_name="nutritioncompletion",
            index=models.Index(fields=["user", "nutrition_date"], name="nutrition_c_user_id_b30901_idx"),
        ),
        migrations.AddConstraint(
            model_name="nutritioncompletion",
            constraint=models.UniqueConstraint(
                fields=("user", "nutrition_date"),
                name="uniq_nutrition_completion_user_date",
            ),
        ),
    ]
