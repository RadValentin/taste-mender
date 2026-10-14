from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.youtube_source_metadata import load_youtube_metadata


class Command(BaseCommand):
    help = "Loads YouTube video metadata from a JSON file into the TrackSource model."

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            completed = load_youtube_metadata()
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Load failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Load complete."))