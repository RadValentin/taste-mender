from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.musicbrainz_api_metadata import gather_musicbrainz_metadata


class Command(BaseCommand):
    help = "Fetches track metadata from MusicBrainz and stores it to disk."

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            completed = gather_musicbrainz_metadata(override_file=True)
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Gathering failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Gathering complete."))