from django.core.management.base import BaseCommand

from apps.common.short_term_memory import purge_expired_short_term_memory


class Command(BaseCommand):
    help = "Delete expired short-term memory entries."

    def handle(self, *args, **options):
        deleted_count = purge_expired_short_term_memory()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} expired short-term memory entries."))
