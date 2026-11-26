"""Rebuildable discussion metadata. JSONL remains the sole authority.

All operations coordinate through the stable discussion lock and legacy log lock.
The snapshot is published only after the authoritative event has been flushed.
"""
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import time

from .storage import FileStore, LockTimeout, append_record, decode, event, locked_log, require

SCHEMA_VERSION = 1


def fingerprint(handle):
    info = os.fstat(handle.fileno())
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checksum(data):
    return sha(json.dumps(data, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))


class DiscussionMetadata:
    """Compact projection with a byte checkpoint and last-event anchor."""

    def __init__(self, discussion, state, offset, anchor_start, anchor_hash, signature, projection):
        self.projection = projection
        self.discussion = discussion
        self.state = state
        self.offset = offset
        self.anchor_start = anchor_start
        self.anchor_hash = anchor_hash
        self.signature = signature

    @classmethod
    def load(cls, path, discussion, projection):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "r", encoding="utf-8") as handle:
                envelope = json.load(handle)
            value = envelope["metadata"]
            if (value["schema"] != SCHEMA_VERSION or value["discussion"] != discussion
                    or checksum(value) != envelope["checksum"]):
                return None
            state = projection.import_state(value["state"])
            offset, anchor_start = value["offset"], value["anchor_start"]
            signature = value["signature"]
            if (type(offset) is not int or type(anchor_start) is not int
                    or not 0 <= anchor_start < offset
                    or type(state["last_seq"]) is not int or state["last_seq"] < 1
                    or not isinstance(signature, list) or len(signature) != 5
                    or not all(type(x) is int for x in signature)
                    or offset > signature[2]):
                return None
            return cls(discussion, state, offset, anchor_start,
                       value["anchor_hash"], signature, projection)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            # Missing, incompatible, or damaged metadata is disposable.
            return None

    @classmethod
    def rebuild(cls, handle, discussion, signature, projection):
        handle.seek(0)
        raw = handle.read()
        records, offset = decode(raw)
        start = raw.rfind(b"\n", 0, offset - 1) + 1
        return cls(discussion, projection.reconstruct(records), offset, start,
                   sha(raw[start:offset]), signature, projection)

    @classmethod
    def recover(cls, handle, path, discussion, projection):
        """Return (snapshot, dirty); incremental recovery only from verified prefix."""
        signature = fingerprint(handle)
        cached = cls.load(path, discussion, projection)
        if cached is not None:
            old = cached.signature
            if old == signature:
                return cached, False
            if old[:2] == signature[:2]:
                require(signature[2] >= cached.offset,
                        "committed discussion prefix truncated")
                # If only metadata timestamps changed at the committed length,
                # revalidate the whole authoritative log rather than trust cache.
                if signature[2] > cached.offset:
                    handle.seek(cached.anchor_start)
                    anchor = handle.read(cached.offset - cached.anchor_start)
                    if sha(anchor) == cached.anchor_hash:
                        handle.seek(cached.offset)
                        raw = handle.read()
                        records, consumed = decode(raw, cached.state["last_seq"] + 1)
                        for record in records:
                            projection.apply(cached.state, record)
                        if consumed:
                            start = raw.rfind(b"\n", 0, consumed - 1) + 1
                            cached.anchor_start = cached.offset + start
                            cached.anchor_hash = sha(raw[start:consumed])
                            cached.offset += consumed
                        cached.signature = signature
                        return cached, True
        return cls.rebuild(handle, discussion, signature, projection), True

    def save(self, path):
        data = {"schema": SCHEMA_VERSION, "discussion": self.discussion,
                "offset": self.offset, "anchor_start": self.anchor_start,
                "anchor_hash": self.anchor_hash, "signature": self.signature,
                "state": self.projection.export_state(self.state)}
        envelope = {"metadata": data, "checksum": checksum(data)}
        fd, temporary = tempfile.mkstemp(prefix=".metadata-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(envelope, handle, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def publish(self, path):
        try:
            self.save(path)
        except OSError as exc:
            # The JSONL operation may already be committed. A cache failure
            # must not report a false write failure or encourage resubmission.
            print("LADP warning: metadata update deferred: " + str(exc), file=sys.stderr)

    def append(self, handle, record):
        # Validate state projection before persisting the event.
        self.projection.apply(self.state, record)
        blob = append_record(handle, self.offset, record)
        self.anchor_start = self.offset
        self.offset += len(blob)
        self.anchor_hash = sha(blob)
        self.signature = fingerprint(handle)


class DiscussionStore(FileStore):
    """Transport plus a rebuildable projection for status and write validation."""

    def __init__(self, root, projection):
        super().__init__(root)
        self.projection = projection

    def meta_path(self, discussion):
        return self.path(discussion).with_suffix(".meta.json")

    def create(self, discussion, actor, payload):
        super().create(discussion, actor, payload)
        # Creation was already committed; metadata can be recovered on next use.
        try:
            self.state(discussion)
        except (LockTimeout, OSError) as exc:
            print("LADP warning: initial metadata deferred: " + str(exc), file=sys.stderr)

    def state(self, discussion):
        deadline = time.monotonic() + 5
        path = self.path(discussion)
        meta = self.meta_path(discussion)
        with locked_log(path, fcntl.LOCK_SH, deadline) as handle:
            snapshot, dirty = DiscussionMetadata.recover(handle, meta, discussion, self.projection)
            if not dirty:
                return snapshot.state
        # Do not promote a shared lock in place. Recheck after exclusive acquisition.
        try:
            with locked_log(path, fcntl.LOCK_EX, deadline) as handle:
                snapshot, dirty = DiscussionMetadata.recover(handle, meta, discussion, self.projection)
                if dirty:
                    snapshot.publish(meta)
        except LockTimeout:
            # The earlier shared read was a valid, linearized snapshot.
            pass
        return snapshot.state

    def append(self, discussion, build):
        deadline = time.monotonic() + 5
        path = self.path(discussion)
        meta = self.meta_path(discussion)
        with locked_log(path, fcntl.LOCK_EX, deadline) as handle:
            snapshot, _ = DiscussionMetadata.recover(handle, meta, discussion, self.projection)
            kind, actor, payload = build(snapshot.state)
            record = event(snapshot.state["last_seq"] + 1, kind, actor, payload)
            snapshot.append(handle, record)
            snapshot.publish(meta)
            return record
