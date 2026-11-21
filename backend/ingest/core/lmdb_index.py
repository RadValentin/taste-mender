import hashlib, lmdb, orjson
import zstandard as zstd
import numpy as np
from collections import defaultdict
from numpy.typing import NDArray
from typing import Iterator


class IndexCompressionError(ValueError):
    """The index's compression metadata or dictionary is invalid."""


def validate_compression_dictionary(data: bytes) -> zstd.ZstdCompressionDict:
    try:
        dictionary = zstd.ZstdCompressionDict(data, dict_type=zstd.DICT_TYPE_FULLDICT)
        if not dictionary.dict_id():
            raise IndexCompressionError("The compression dictionary must have a nonzero ID")
        return dictionary
    except zstd.ZstdError as exc:
        raise IndexCompressionError("Invalid Zstandard compression dictionary") from exc


class LMDBTrackIndex:
    """
    Disk-based index that stores track data grouped by their MusicBrainz ID (mbid), a 36 character
    string in UUID format. Interface mimics standard Python dict.

    External API view: `uuid-key: [ {item1}, {item2}, ... ]`

    Keys are internally they're serialized to bytes. Externally they're strings.
    Values are stored compressed (optional) and serialized to JSON bytes. Externally they're
    returned as lists of JSON dicts as tracks can have duplicates.
    """

    def __init__(
        self, path, map_size=2 * 1024**3, disable_compression=False, batch=10000,
        compression_dictionary: bytes | None = None,
    ):
        self.env = lmdb.open(
            path,
            map_size=map_size,
            subdir=True,
            max_dbs=2,
            lock=True,
            writemap=True,
            map_async=True,
            metasync=False,
            sync=False,
            readahead=True,
        )
        try:
            self.db = self.env.open_db(b"main", create=True)
            self.disable_compression = disable_compression
            dictionary = self._load_compression_dictionary(compression_dictionary)
            if not disable_compression:
                self.compressor = zstd.ZstdCompressor(level=1, dict_data=dictionary)
                self.decompressor = zstd.ZstdDecompressor(dict_data=dictionary)
        except (IndexCompressionError, zstd.ZstdError):
            self.env.close()
            raise
        self.stats = defaultdict(int)
        # batch writes
        self._txn = None
        self._n = 0
        self._batch = batch

    def _load_compression_dictionary(
        self, requested: bytes | None,
    ) -> zstd.ZstdCompressionDict | None:
        with self.env.begin(write=requested is not None) as txn:
            mode = txn.get(b"compression_mode")
            stored = txn.get(b"compression_dictionary")
            digest = txn.get(b"compression_dictionary_sha256")

            if mode is None:
                if stored is not None or digest is not None:
                    raise IndexCompressionError("Incomplete compression metadata in track index")
                if requested is None:
                    return None
                if self.disable_compression:
                    raise IndexCompressionError("A dictionary requires compression to be enabled")
                if txn.stat(db=self.db)["entries"] or txn.get(b"ingest_complete"):
                    raise IndexCompressionError("Cannot add a dictionary to an existing track index")
                dictionary = validate_compression_dictionary(requested)
                txn.put(b"compression_mode", b"zstd-dictionary-v1")
                txn.put(b"compression_dictionary", requested)
                txn.put(b"compression_dictionary_sha256", hashlib.sha256(requested).digest())
                return dictionary

            if mode != b"zstd-dictionary-v1":
                raise IndexCompressionError("Unsupported track index compression mode")
            if self.disable_compression:
                raise IndexCompressionError("Track index requires dictionary compression")
            if stored is None or digest is None or hashlib.sha256(stored).digest() != digest:
                raise IndexCompressionError("Missing or corrupt track index compression dictionary")
            if requested is not None and requested != stored:
                raise IndexCompressionError("The requested dictionary does not match the track index")
            return validate_compression_dictionary(stored)

    def _serialize_key(self, key: str) -> bytes:
        """Convert a key to bytes representation for internal use"""
        return key.encode()

    def _deserialize_key(self, key: bytes) -> str:
        """Convert a key from bytes to string for external use"""
        return key.decode()

    def _serialize_values(self, data: list) -> bytes:
        """Compress (optional) and encode values to JSON bytes"""
        json_bytes = orjson.dumps(data)
        if not self.disable_compression:
            compressed = self.compressor.compress(json_bytes)
            return compressed
        return json_bytes

    def _deserialize_values(self, data: bytes) -> list:
        """Decompress (optional) and decode values from JSON bytes to list of dicts"""
        if self.disable_compression:
            return orjson.loads(data)

        try:
            decompressed = self.decompressor.decompress(data)
        except zstd.ZstdError as exc:
            try:
                dictionary_id = zstd.get_frame_parameters(data).dict_id
            except zstd.ZstdError:
                raise exc
            if dictionary_id:
                raise IndexCompressionError("Cannot decompress track index with its stored dictionary") from exc
            raise
        return orjson.loads(decompressed)

    def append(self, key: str, value):
        key_bytes = self._serialize_key(key)

        if self._txn is None:
            self._txn = self.env.begin(write=True, db=self.db, buffers=True)
            self._n = 0

        current = self._txn.get(key_bytes)
        if current:
            lst = self._deserialize_values(current)
            lst.append(value)
            self.stats["duplicates"] += 1
        else:
            lst = [value]

        self._txn.put(key_bytes, self._serialize_values(lst))
        self._n += 1
        if self._n >= self._batch:
            self._txn.commit()
            self._txn = None

    def __setitem__(self, key: str, values):
        key_bytes = self._serialize_key(key)
        if self._txn is None:
            self._txn = self.env.begin(write=True, db=self.db)
            self._n = 0
        if values is None:
            self._txn.delete(key_bytes)
        else:
            if not isinstance(values, list):
                raise ValueError("Value must be a list")
            self._txn.put(key_bytes, self._serialize_values(values))

        self._n += 1
        if self._n >= self._batch:
            self._txn.commit()
            self._txn = None

    def get(self, key: str, default=None) -> list | None:
        key_bytes = self._serialize_key(key)

        txn = self._txn if self._txn is not None else self.env.begin(db=self.db)
        val = txn.get(key_bytes)
        if val is None:
            return default
        return self._deserialize_values(val)

    def __getitem__(self, key: str) -> list | None:
        return self.get(key)

    def items(self) -> Iterator[tuple[str, list]]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for key_bytes, values_bytes in cur:
                    yield self._deserialize_key(key_bytes), self._deserialize_values(values_bytes)

    def iter_prefix(self, prefix: bytes) -> Iterator[tuple[bytes, bytes]]:
        """Yield committed raw key-value pairs with the given prefix in key order."""
        with self.env.begin(db=self.db) as txn, txn.cursor() as cur:
            if prefix and not cur.set_range(prefix):
                return
            for key, value in cur:
                if not key.startswith(prefix):
                    break
                yield key, value

    def keys(self) -> set[str]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                return set(
                    self._deserialize_key(key)
                    for key in cur.iternext(keys=True, values=False)
                )

    def keys_np(self) -> NDArray[np.object_]:
        """Return committed LMDB keys as an array of bytes in key order."""
        with self.env.begin(db=self.db) as txn, txn.cursor() as cursor:
            return np.fromiter(
                cursor.iternext(keys=True, values=False),
                dtype=object,
                count=txn.stat()["entries"],
            )

    def first_key(self) -> str | None:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    key_bytes = cur.key()
                    return self._deserialize_key(key_bytes)
                return None

    def values(self) -> Iterator[list]:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for _, values_bytes in cur:
                    yield self._deserialize_values(values_bytes)

    def first_value(self, raw=False) -> tuple | None:
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                if cur.first():
                    _, values_bytes = cur.item()
                    if raw:
                        return values_bytes
                    return self._deserialize_values(values_bytes)
                return None

    def flush(self):
        # commit any pending batch then fsync (needed due to sync=False in env.open)
        if self._txn is not None:
            self._txn.commit()
            self._txn = None
            self._n = 0
        self.env.sync()

    def is_complete(self) -> bool:
        with self.env.begin() as txn:
            return txn.get(b"ingest_complete") == b"1"

    def mark_complete(self):
        self.flush()
        with self.env.begin(write=True) as txn:
            txn.put(b"ingest_complete", b"1")
        self.env.sync(True)

    def close(self):
        self.flush()
        self.env.close()

    def size_pages(self) -> int:
        with self.env.begin(db=self.db) as txn:
            st = txn.stat()
            return (st["branch_pages"] + st["leaf_pages"] + st["overflow_pages"]) * st["psize"]

    def map_size(self) -> int:
        return self.env.info()["map_size"]