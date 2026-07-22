# -*- coding: utf-8 -*-
"""
Tests for lmfdb.schema_refresh.

These use stub database/listener objects, so they exercise the refresher's
control flow (subscribe, poll, refresh, failure, fork handling) without
needing a psycodict that provides the LISTEN/NOTIFY API; they pass against
any psycodict version.
"""

from lmfdb.schema_refresh import SCHEMA_CHANNEL, SchemaRefresher


class StubListener:
    def __init__(self, db):
        self._db = db
        self.closed = False

    def poll(self, timeout=0.0):
        if self._db.poll_error is not None:
            raise self._db.poll_error
        batch, self._db.pending = self._db.pending, []
        return batch

    def close(self):
        self.closed = True


class StubDB:
    """
    Duck-types the (tiny) psycodict surface the refresher touches.
    """
    def __init__(self):
        self.refreshes = 0
        self.pending = []
        self.listeners = []
        self.listen_error = None
        self.poll_error = None
        self.refresh_error = None

    def listener(self):
        if self.listen_error is not None:
            raise self.listen_error
        listener = StubListener(self)
        self.listeners.append(listener)
        return listener

    def refresh_tables(self):
        if self.refresh_error is not None:
            raise self.refresh_error
        self.refreshes += 1


def test_unavailable_psycodict_is_a_noop():
    # An object with neither listener() nor refresh_tables(), like psycodict
    # before 1.0: the refresher must disable itself, not crash the request.
    refresher = SchemaRefresher(db=object())
    refresher.check()
    refresher.check()
    assert refresher._listener is None


def test_subscribe_then_notify():
    db = StubDB()
    refresher = SchemaRefresher(db=db)
    # The first check subscribes and does a catch-up refresh (notifications
    # sent before LISTEN are lost, so a new subscriber cannot assume it has
    # seen everything).
    refresher.check()
    assert len(db.listeners) == 1
    assert db.refreshes == 1
    # A quiet poll does not refresh.
    refresher.check()
    assert db.refreshes == 1
    # One batch of notifications = one refresh; other channels are ignored.
    db.pending = [
        (SCHEMA_CHANNEL, "nf_fields"),
        (SCHEMA_CHANNEL, "ec_curvedata"),
        ("some_other_channel", "ignored"),
    ]
    refresher.check()
    assert db.refreshes == 2
    refresher.check()
    assert db.refreshes == 2


def test_subscription_failure_backs_off_then_recovers():
    db = StubDB()
    db.listen_error = RuntimeError("connection refused")
    refresher = SchemaRefresher(db=db, retry_interval=1000)
    refresher.check()
    assert refresher._listener is None
    assert db.refreshes == 0
    # Within the retry interval, no new attempt is made even though the
    # database has recovered.
    db.listen_error = None
    refresher.check()
    assert refresher._listener is None
    # Once the interval has passed, it subscribes and catches up.
    refresher._next_attempt = 0.0
    refresher.check()
    assert len(db.listeners) == 1
    assert db.refreshes == 1


def test_lost_listener_resubscribes_with_catchup():
    db = StubDB()
    refresher = SchemaRefresher(db=db, retry_interval=0.0)
    refresher.check()
    assert db.refreshes == 1
    db.poll_error = RuntimeError("server closed the connection unexpectedly")
    refresher.check()
    assert refresher._listener is None
    assert db.listeners[0].closed
    db.poll_error = None
    # The resubscription's catch-up refresh covers notifications that were
    # lost while disconnected.
    refresher.check()
    assert len(db.listeners) == 2
    assert db.refreshes == 2


def test_failed_refresh_drops_listener_for_retry():
    db = StubDB()
    refresher = SchemaRefresher(db=db, retry_interval=0.0)
    db.refresh_error = RuntimeError("could not read meta_tables")
    refresher.check()
    # The catch-up refresh failed: rather than staying subscribed with stale
    # metadata, the listener is dropped so the next check retries in full.
    assert refresher._listener is None
    assert db.refreshes == 0
    db.refresh_error = None
    refresher.check()
    assert db.refreshes == 1
    assert refresher._listener is not None


def test_hot_standby_disables_permanently():
    class RecoveryError(RuntimeError):
        sqlstate = "25006"

    db = StubDB()
    db.listen_error = RecoveryError("cannot execute LISTEN during recovery")
    refresher = SchemaRefresher(db=db, retry_interval=0.0)
    refresher.check()
    assert refresher._listener is None
    # Permanent: even after the retry interval (0s here) and with the error
    # cleared, no new subscription is attempted -- a standby can never
    # deliver notifications, so retrying would just warn forever.
    db.listen_error = None
    refresher.check()
    assert db.listeners == []
    assert db.refreshes == 0


def test_forked_worker_builds_its_own_listener():
    db = StubDB()
    refresher = SchemaRefresher(db=db)
    refresher.check()
    # Simulate a fork: the recorded pid no longer matches this process.
    refresher._pid = -1
    refresher.check()
    # The inherited listener is abandoned *without* close (its socket is
    # shared with the parent process) and a fresh one is built, followed by
    # the usual catch-up refresh.
    assert len(db.listeners) == 2
    assert not db.listeners[0].closed
    assert db.refreshes == 2
