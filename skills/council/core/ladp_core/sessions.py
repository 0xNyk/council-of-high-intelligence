"""Private local session checkpoints; never part of the discussion log."""
import json
import os
import stat
import tempfile
from pathlib import Path

from .storage import ID_RE, require


def private_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
            and not info.st_mode & 0o077, "session directory must be private: " + str(path))


def read_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "r", encoding="utf-8") as handle:
        info = os.fstat(handle.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and not info.st_mode & 0o077, "session file must be private")
        return json.load(handle)


def atomic_private(path, data):
    private_directory(path.parent)
    fd, temp = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class SessionStore:
    def __init__(self, discussion_root, root=None):
        # Tests with LADP_HOME must never leak credentials into the default store.
        self.root = Path(root) if root is not None else (Path(discussion_root) / ".sessions" if os.environ.get("LADP_HOME")
                     else Path.home() / ".ladp" / "sessions")

    def path(self, discussion, actor, suffix=".json"):
        require(ID_RE.fullmatch(discussion) and ID_RE.fullmatch(actor), "invalid session ID")
        return self.root / discussion / (actor + suffix)

    def save_identity(self, discussion, actor, token):
        path = self.path(discussion, actor)
        private_directory(self.root)
        private_directory(path.parent)
        if path.exists() or path.is_symlink():
            existing = read_private(path)
            require(existing == {"discussion": discussion, "actor": actor, "token": token},
                    "saved session conflicts with credentials")
            return
        atomic_private(path, {"discussion": discussion, "actor": actor, "token": token})

    def token(self, discussion, actor):
        path = self.path(discussion, actor)
        try:
            private_directory(self.root)
            # Do not create a discussion directory just to look for a credential.
            if not path.parent.exists():
                return None
            private_directory(path.parent)
            data = read_private(path)
        except FileNotFoundError:
            return None
        require(data.get("discussion") == discussion and data.get("actor") == actor
                and isinstance(data.get("token"), str), "invalid saved session")
        return data["token"]

    def save_commitment(self, discussion, actor, content, nonce):
        atomic_private(self.path(discussion, actor, ".commit.json"),
                       {"content": content, "nonce": nonce})

    def commitment(self, discussion, actor):
        try:
            return read_private(self.path(discussion, actor, ".commit.json"))
        except FileNotFoundError:
            return None

    def actors(self, discussion):
        require(ID_RE.fullmatch(discussion), "invalid discussion ID")
        if not self.root.exists():
            return []
        private_directory(self.root)
        folder = self.root / discussion
        if not folder.exists():
            return []
        private_directory(folder)
        return sorted(p.stem for p in folder.glob("*.json")
                      if ID_RE.fullmatch(p.stem))
