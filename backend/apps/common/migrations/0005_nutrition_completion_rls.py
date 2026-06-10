from django.db import migrations


USER_ID_EXPR = "NULLIF(current_setting('app.current_user_id', true), '')::bigint"


def _enable_nutrition_completion_rls(apps, schema_editor):
    table = "nutrition_completion"
    policy = f"{table}_user_isolation"
    statements = [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy} ON {table}",
        (
            f"CREATE POLICY {policy} ON {table} "
            f"USING (user_id = {USER_ID_EXPR}) "
            f"WITH CHECK (user_id = {USER_ID_EXPR})"
        ),
    ]
    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def _disable_nutrition_completion_rls(apps, schema_editor):
    table = "nutrition_completion"
    policy = f"{table}_user_isolation"
    statements = [
        f"DROP POLICY IF EXISTS {policy} ON {table}",
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY",
    ]
    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0004_user_owned_row_level_security"),
        ("nutrition", "0002_nutritioncompletion"),
    ]

    operations = [
        migrations.RunPython(_enable_nutrition_completion_rls, _disable_nutrition_completion_rls),
    ]
