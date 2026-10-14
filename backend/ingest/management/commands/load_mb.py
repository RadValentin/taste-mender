from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.musicbrainz_api_metadata import load_musicbrainz_metadata


class Command(BaseCommand):
    help = "Loads MusicBrainz metadata from a JSON file into the Track model."

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            completed = load_musicbrainz_metadata()
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Load failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Load complete."))