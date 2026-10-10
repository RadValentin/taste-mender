from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.musicbrainz_api_metadata import gather_musicbrainz_metadata


class Command(BaseCommand):
    help = "Fetches track metadata from MusicBrainz and stores it to disk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=int,
            default=10,
            help="How many tracks to process.",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        batch_size = options.get("batch", 10)

        try:
            completed = gather_musicbrainz_metadata(batch_size=batch_size)
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Gathering failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Gathering complete."))