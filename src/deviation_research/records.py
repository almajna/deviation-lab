"""Canonical records and transactional, append-only scientific memory."""
import hashlib
import json
from pathlib import Path
import sqlite3


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+"\n")


def source_hash():
    root = Path(__file__).resolve().parent
    return sha({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))})


class Memory:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(key TEXT PRIMARY KEY, state TEXT NOT NULL, record TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS no_event_update BEFORE UPDATE ON events
          BEGIN SELECT RAISE(ABORT, 'append only'); END;
        CREATE TRIGGER IF NOT EXISTS no_event_delete BEFORE DELETE ON events
          BEGIN SELECT RAISE(ABORT, 'append only'); END;
        """)
        self.verify()

    def close(self):
        self.db.close()

    def _event(self, kind, entity, payload, parents=()):
        last = self.db.execute("SELECT seq,record FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq, previous = (last[0]+1, json.loads(last[1])["sha256"]) if last else (0, None)
        value = dict(version="research-events-1", seq=seq, kind=kind, entity=entity,
                     parents=list(parents), payload=payload, previous_sha256=previous)
        value["sha256"] = sha(value)
        self.db.execute("INSERT INTO events VALUES (?,?)", (seq, encode(value)))
        return value["sha256"]

    def event(self, kind, entity, payload, parents=()):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = self._event(kind, entity, payload, parents)
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def reserve(self, key, record):
        """Atomic at-most-once reservation, including failed or interrupted ideas."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT state FROM runs WHERE key=?", (key,)).fetchone()
            if old:
                self._event("duplicate_skipped", key, {"previous_state": old[0]})
            else:
                self.db.execute("INSERT INTO runs VALUES (?,?,?)", (key, "running", encode(record)))
                self._event("experiment_started", key, record, [record["plan_sha256"]])
            self.db.execute("COMMIT")
            return old is None
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def finish(self, key, state, record):
        if state not in {"completed", "failed", "rejected"}:
            raise ValueError("invalid terminal state")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            changed = self.db.execute("UPDATE runs SET state=?,record=? WHERE key=? AND state='running'",
                                      (state, encode(record), key)).rowcount
            if changed != 1:
                raise ValueError("missing or terminal experiment")
            self._event("experiment_"+state, key, record, [key])
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def verify(self):
        self.db.execute("BEGIN")
        try:
            self._verify()
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _verify(self):
        previous = None
        expected_runs = {}
        index = 0
        for seq, row in self.db.execute("SELECT seq,record FROM events ORDER BY seq"):
            v = json.loads(row)
            h = v.pop("sha256")
            if seq != index or v["seq"] != seq or v["previous_sha256"] != previous or sha(v) != h:
                raise ValueError("research memory hash chain mismatch")
            if v["kind"] == "experiment_started":
                if v["entity"] in expected_runs:
                    raise ValueError("duplicate scientific reservation")
                expected_runs[v["entity"]] = ("running", v["payload"])
            if v["kind"] in {"experiment_completed", "experiment_failed", "experiment_rejected"}:
                if expected_runs.get(v["entity"], (None,))[0] != "running":
                    raise ValueError("terminal scientific record without reservation")
                expected_runs[v["entity"]] = (v["kind"].removeprefix("experiment_"), v["payload"])
            previous = h
            index += 1
        actual = {k: (state, json.loads(record)) for k, state, record in self.db.execute("SELECT key,state,record FROM runs")}
        if expected_runs != actual:
            raise ValueError("run index differs from append-only evidence")

    def inspect(self):
        self.verify()
        return [{"key": k, "state": state, "record": json.loads(record)}
                for k, state, record in self.db.execute("SELECT key,state,record FROM runs ORDER BY key")]

    def export(self, destination):
        self.verify()
        Path(destination).write_text("".join(r[0]+"\n" for r in self.db.execute("SELECT record FROM events ORDER BY seq")))
