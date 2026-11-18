import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import UUID


MANIFEST_VERSION = 1


@dataclass(frozen=True)
class DatasetManifest:
    """
    Class for working with manifest data from the DB (`Manifest` model) or from the feature matrix.
    Provides an easy way for serializing/deserializing the provenance data.
    """
    manifest_version: int
    run_id: UUID
    generated_at: datetime
    track_count: int
    app_version: str = ""

    def to_json(self) -> str:
        return json.dumps({
            **asdict(self),
            "run_id": str(self.run_id),
            "generated_at": self.generated_at.astimezone(timezone.utc).isoformat(),
        })

    @classmethod
    def from_json(cls, value: str) -> "DatasetManifest":
        try:
            data = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError("Manifest must contain valid JSON.") from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "DatasetManifest":
        if not isinstance(data, dict):
            raise ValueError("Manifest must be a JSON object.")
        version = data.get("manifest_version")
        if type(version) is not int or version != MANIFEST_VERSION:
            raise ValueError(f"Unsupported manifest version {version!r}; expected {MANIFEST_VERSION}.")
        count = data.get("track_count")
        if type(count) is not int or count < 0:
            raise ValueError("Manifest track_count must be a non-negative integer.")
        try:
            run_id = UUID(str(data["run_id"]))
            generated_at = data["generated_at"]
            if isinstance(generated_at, str):
                generated_at = datetime.fromisoformat(generated_at)
            if not isinstance(generated_at, datetime) or generated_at.utcoffset() is None:
                raise ValueError("A timezone-aware timestamp is required.")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Manifest requires a UUID run_id and a timezone-aware generated_at.") from exc
        app_version = data.get("app_version", "")
        if not isinstance(app_version, str):
            raise ValueError("Manifest app_version must be a string.")
        return cls(version, run_id, generated_at, count, app_version)
