from django.db import migrations


USER_ID_EXPR = "NULLIF(current_setting('app.current_user_id', true), '')::bigint"


USER_OWNED_TABLES = [
    "user_profile",
    "user_preferences",
    "plan",
    "workout_intent_analysis",
    "workout_completion",
    "short_term_memory_entry",
]


def _enable_rls_sql():
    statements = []
    for table in USER_OWNED_TABLES:
        policy = f"{table}_user_isolation"
        statements.extend(
            [
                f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
                f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
                f"DROP POLICY IF EXISTS {policy} ON {table}",
                (
                    f"CREATE POLICY {policy} ON {table} "
                    f"USING (user_id = {USER_ID_EXPR}) "
                    f"WITH CHECK (user_id = {USER_ID_EXPR})"
                ),
            ]
        )
    return ";\n".join(statements) + ";"


def _disable_rls_sql():
    statements = []
    for table in reversed(USER_OWNED_TABLES):
        policy = f"{table}_user_isolation"
        statements.extend(
            [
                f"DROP POLICY IF EXISTS {policy} ON {table}",
                f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY",
                f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY",
            ]
        )
    return ";\n".join(statements) + ";"


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0003_shorttermmemoryentry"),
        ("profiles", "0003_userprofile_snapshots"),
        ("workout", "0003_workoutcompletion"),
    ]

    operations = [
        migrations.RunSQL(sql=_enable_rls_sql(), reverse_sql=_disable_rls_sql()),
    ]
