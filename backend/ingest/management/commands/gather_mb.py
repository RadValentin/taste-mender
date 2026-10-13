from typing import Any
from django.core.management.base import BaseCommand, CommandError
from ingest.enrichments.musicbrainz_api_metadata import gather_musicbrainz_metadata


class Command(BaseCommand):
    help = "Fetches track metadata from MusicBrainz and stores it to disk."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            dest="batch_size",
            type=int,
            default=10,
            help="How many tracks to process",
        )

        parser.add_argument(
            "--override",
            dest="override_file",
            action="store_true",
            help="Build the output file from scratch on every run",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            completed = gather_musicbrainz_metadata(
                batch_size=options["batch_size"],
                override_file=options["override_file"],
            )
        except Exception as ex:
            raise CommandError(str(ex))

        if not completed:
            raise CommandError("Gathering failed or was aborted.")

        self.stdout.write(self.style.SUCCESS("Gathering complete."))
