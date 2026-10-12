from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.youtube_source_metadata import gather_youtube_metadata


class Command(BaseCommand):
    help = "Fetches track sources from YouTube and stores them on disk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=int,
            default=1,
            help="How many tracks to process.",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        batch_size = options.get("batch", 10)

        try:
            completed = gather_youtube_metadata(batch_size=batch_size, override_file=True)
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Gathering failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Gathering complete."))