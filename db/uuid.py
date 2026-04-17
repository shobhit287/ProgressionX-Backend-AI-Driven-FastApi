"""
Time-ordered UUIDv7 generator.

Why v7 over v4:
- v7 UUIDs have a millisecond timestamp as the leading 48 bits, so inserts into
  B-tree indexes stay roughly sequential instead of scattering across pages.
  Matters at >1M rows; ~free to adopt now while the DB is small.

Data safety:
- v4 and v7 share the same 16-byte wire format and the same Postgres UUID type,
  so existing v4 rows remain valid and queries/foreign keys are unaffected.
- Only newly inserted rows get v7 ids from this point forward.

Python 3.14 adds stdlib `uuid.uuid7()`; on older versions we use the
Rust-backed `uuid-utils` package and coerce to a stdlib `uuid.UUID` so
SQLAlchemy's `UUID(as_uuid=True)` columns accept it transparently.
"""

import uuid as _uuid

_stdlib_uuid7 = getattr(_uuid, "uuid7", None)

if _stdlib_uuid7 is not None:
    def new_uuid() -> _uuid.UUID:
        return _stdlib_uuid7()
else:
    from uuid_utils import uuid7 as _ext_uuid7

    def new_uuid() -> _uuid.UUID:
        return _uuid.UUID(bytes=_ext_uuid7().bytes)


__all__ = ["new_uuid"]
