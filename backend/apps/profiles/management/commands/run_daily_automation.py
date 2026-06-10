from django.core.management.base import BaseCommand

from apps.profiles.services.daily_automation import run_daily_automation


class Command(BaseCommand):
    help = "Prepare daily weather greeting and nutrition plans for active users."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", action="append", type=int, dest="user_ids")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--skip-weather", action="store_true")
        parser.add_argument("--skip-greeting", action="store_true")
        parser.add_argument("--skip-nutrition", action="store_true")

    def handle(self, *args, **options):
        summary = run_daily_automation(
            user_ids=options.get("user_ids"),
            force=options.get("force", False),
            skip_weather=options.get("skip_weather", False),
            skip_greeting=options.get("skip_greeting", False),
            skip_nutrition=options.get("skip_nutrition", False),
        )
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")
