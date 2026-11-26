"""LADP v1 local append-only transport. No discussion policy here."""
import fcntl
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VERSION = 1
MAX_EVENT = 1024 * 1024
ID_RE = re.compile(r"[0-9a-f]{32}\Z")


class ProtocolError(Exception):
    pass


class LockTimeout(ProtocolError):
    pass


def acquire_lock(handle, mode, deadline):
    """Try once even at a zero deadline; never wait indefinitely on flock."""
    while True:
        try:
            fcntl.flock(handle, mode | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LockTimeout("file lock acquisition timed out")
            time.sleep(min(0.025, remaining))


def require(condition, message):
    if not condition:
        raise ProtocolError(message)


def event(seq, kind, actor, payload):
    return {
        "v": VERSION, "seq": seq, "id": uuid.uuid4().hex,
        "at": datetime.now(timezone.utc).isoformat(),
        "type": kind, "actor": actor, "data": payload,
    }


def encode(record):
    data = (json.dumps(record, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")
    require(len(data) <= MAX_EVENT, "event exceeds 1 MiB")
    return data


def decode(raw, start_seq=1):
    """Decode complete records starting at start_seq; retain incomplete tail."""
    records = []
    offset = 0
    for part in raw.split(b"\n")[:-1]:
        line = part + b"\n"
        try:
            require(len(line) <= MAX_EVENT, "oversized event")
            item = json.loads(line)
            require(isinstance(item, dict) and item.get("v") == VERSION
                    and type(item.get("seq")) is int
                    and item["seq"] == start_seq + len(records)
                    and isinstance(item.get("id"), str)
                    and isinstance(item.get("type"), str)
                    and isinstance(item.get("actor"), str)
                    and isinstance(item.get("data"), dict),
                    "invalid event envelope at line " + str(len(records) + 1))
        except (ValueError, UnicodeError) as exc:
            raise ProtocolError("invalid complete JSONL record") from exc
        records.append(item)
        offset += len(line)
    if start_seq == 1:
        require(bool(records) and records[0]["type"] == "created", "missing creation event")
    return records, offset


@contextmanager
def locked_log(path, mode, deadline):
    """Stable sidecar lock protects log + snapshot; log lock bridges v1.1 clients."""
    path = Path(path)
    writable = mode == fcntl.LOCK_EX
    fd = os.open(path, (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW)
    with os.fdopen(fd, "r+b" if writable else "rb") as handle:
        lock_fd = os.open(path.with_suffix(".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, "r+b") as guard:
            acquire_lock(guard, mode, deadline)
            acquire_lock(handle, mode, deadline)
            yield handle


def append_record(handle, offset, record):
    """Append a validated event and repair only an incomplete, uncommitted tail."""
    blob = encode(record)
    if os.fstat(handle.fileno()).st_size != offset:
        handle.truncate(offset)
    handle.seek(offset)
    handle.write(blob)
    handle.flush()
    os.fsync(handle.fileno())
    return blob


class LogReader:
    """Per-command cache of a verified append-only prefix; no lock while idle."""
    def __init__(self, path):
        self.path = path
        self.records = []
        self.offset = 0
        self.signature = None
        self.inode = None

    def refresh(self, deadline):
        with locked_log(self.path, fcntl.LOCK_SH, deadline) as handle:
            info = os.fstat(handle.fileno())
            inode = (info.st_dev, info.st_ino)
            require(self.inode is None or self.inode == inode, "discussion file replaced")
            require(info.st_size >= self.offset, "committed discussion prefix truncated")
            signature = (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if self.signature == signature:
                return False
            handle.seek(self.offset)
            new, consumed = decode(handle.read(), len(self.records) + 1)
            self.records.extend(new)
            self.offset += consumed
            self.inode = inode
            self.signature = signature
            return bool(new)



class FileStore:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("LADP_HOME",
                         str(Path.home() / ".ladp" / "discussions"))).expanduser()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def path(self, discussion):
        require(isinstance(discussion, str) and ID_RE.fullmatch(discussion),
                "discussion ID must be 32 lowercase hex characters")
        return self.root / (discussion + ".jsonl")

    def ids(self):
        return sorted(p.stem for p in self.root.glob("*.jsonl")
                      if ID_RE.fullmatch(p.stem) and not p.is_symlink())

    def create(self, discussion, actor, payload):
        """Publish a complete first record atomically; never overwrite."""
        path = self.path(discussion)
        fd, temp = tempfile.mkstemp(prefix=".create-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encode(event(1, "created", actor, payload)))
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temp, path)
        finally:
            os.unlink(temp)

    def reader(self, discussion):
        return LogReader(self.path(discussion))

    def read(self, discussion):
        reader = self.reader(discussion)
        reader.refresh(time.monotonic() + 5)
        return reader.records

    def append(self, discussion, build):
        """Read, validate, assign sequence and append within one exclusive lock."""
        with locked_log(self.path(discussion), fcntl.LOCK_EX, time.monotonic() + 5) as handle:
            records, offset = decode(handle.read())
            kind, actor, payload = build(records)
            record = event(len(records) + 1, kind, actor, payload)
            append_record(handle, offset, record)
            return record
