"""Advisory checks for the database and the feature matrix used by this process."""

import logging
from dataclasses import fields

from django.core.checks import Warning, register
from django.db import DatabaseError, connections

from recommend_api.dataset_manifest import DatasetManifest
from recommend_api.models import Manifest, Track


log = logging.getLogger("recommend_api.startup")
REBUILD_HINT = "Run build_db to rebuild both outputs together, or deploy a matching database and feature archive."


@register("dataset", deploy=True)
def check_dataset(app_configs, databases=None, **kwargs):
    # Django checks must not query a DB unless its alias was explicitly supplied.
    if not databases or "default" not in databases:
        return []

    from recommend_api.services.recommender import STORE

    warnings = []
    track_counts = {} # for checking the number of tracks in manifest, db, feature matrix
    db_manifest = None # manifest data stored in the Postgres database
    matrix_manifest = None # manifest data stored in the feature matrix file
    try:
        track_counts["database"] = Track.objects.count()
        record = Manifest.objects.first()
        if record is None:
            warnings.append(Warning("Database has no completed ingest manifest.", hint=REBUILD_HINT, id="recommend_api.W001"))
        else:
            try:
                db_manifest = DatasetManifest.from_dict({
                    field.name: getattr(record, field.name) for field in fields(DatasetManifest)
                })
            except ValueError as exc:
                warnings.append(Warning(f"Database ingest manifest is invalid: {exc}", hint=REBUILD_HINT, id="recommend_api.W008"))
    except DatabaseError:
        warnings.append(Warning(
            "Database ingest manifest could not be checked.",
            hint="Ensure the database is available and run python manage.py migrate, then repeat the dataset check.",
            id="recommend_api.W007",
        ))

    matrix_manifest = STORE.manifest
    if not getattr(STORE, "_loaded", False):
        warnings.append(Warning("Feature matrix is unavailable; dataset consistency cannot be verified.", hint=REBUILD_HINT, id="recommend_api.W006"))
    else:
        track_counts["feature matrix"] = STORE.feature_matrix.shape[0]
        track_counts["MBID index"] = len(STORE.mbid_to_idx)
        if matrix_manifest is None:
            reason = f"is invalid: {STORE.manifest_error}" if STORE.manifest_error else "is missing"
            warnings.append(Warning(f"Feature matrix ingest manifest {reason}.", hint=REBUILD_HINT, id="recommend_api.W002"))

    if db_manifest is not None:
        track_counts["database manifest"] = db_manifest.track_count
    if matrix_manifest is not None:
        track_counts["feature matrix manifest"] = matrix_manifest.track_count
    if db_manifest is not None and matrix_manifest is not None:
        if db_manifest.run_id != matrix_manifest.run_id:
            warnings.append(Warning(
                f"Ingest run IDs differ: database={db_manifest.run_id}, feature matrix={matrix_manifest.run_id}.",
                hint=REBUILD_HINT, id="recommend_api.W003",
            ))
        if db_manifest.generated_at != matrix_manifest.generated_at:
            warnings.append(Warning(
                f"Ingest generation timestamps differ: database={db_manifest.generated_at.isoformat()}, "
                f"feature matrix={matrix_manifest.generated_at.isoformat()}.",
                hint=REBUILD_HINT, id="recommend_api.W004",
            ))
    if len(set(track_counts.values())) > 1:
        detail = ", ".join(f"{name}={count:,}" for name, count in track_counts.items())
        warnings.append(Warning(f"Dataset track counts differ: {detail}.", hint=REBUILD_HINT, id="recommend_api.W005"))
    return warnings


def warn_dataset_mismatch():
    """Called after WSGI/ASGI initialization, including Django's runserver handler."""
    try:
        warnings = check_dataset(None, databases=["default"])
        if warnings:
            messages = [f"  - {warning.msg}" for warning in warnings]
            hints = list(dict.fromkeys(warning.hint for warning in warnings if warning.hint))
            log.warning("%s", "\n".join([
                "\nWARNING: Dataset consistency",
                *messages,
                "",
                *hints,
                "The server will continue to run.\n",
            ]))
    finally:
        # Gunicorn preloads the WSGI app before forking; never inherit this DB connection.
        connections.close_all()
