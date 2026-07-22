# -*- coding: utf-8 -*-
"""
Keep a long-running website's table metadata in sync with the database.

psycodict reads each table's columns, types and sort information from the
database once, when the connection is created.  A website process therefore
does not see schema changes made elsewhere: after a column is dropped its
queries still mention the column and fail, and a newly added column stays
invisible, until every worker process is restarted.

psycodict provides the two halves of the remedy:

- ``db.refresh_tables()`` re-reads the schema and updates the table objects
  in place, so references held by application code stay valid
  (roed314/psycodict#99);
- schema-changing operations (``create_table``, ``drop_table``,
  ``rename_table``, ``add_column``, ``drop_column`` and the reload swap)
  announce themselves via PostgreSQL's LISTEN/NOTIFY on the channel
  ``psycodict_schema``, with the affected table's name as payload, and
  ``db.listener()`` subscribes to that channel (roed314/psycodict#111).

This module ties the two together for the website.  Each worker process owns
a :class:`SchemaRefresher`, driven by a non-blocking ``check()`` from a
``before_request`` hook: when a schema-change notification has arrived, the
worker refreshes its table metadata before handling the request.

psycodict deliberately ships the notification API without threads, callbacks
or automatic reconnection, leaving those policies to the application.  The
policies chosen here:

- **No background thread.**  Web workers spend their life handling requests,
  so polling at request boundaries is both sufficient and free of the races a
  refresh-from-another-thread would invite.  An idle worker can lag behind
  until its next request, which is harmless: with no requests there are no
  queries to fail.  A non-blocking poll on an idle connection is just a
  socket read, so doing it every request costs nothing measurable.
- **Reconnect with catch-up.**  If the listening connection is lost, any
  notifications sent before a new ``LISTEN`` is issued are gone (PostgreSQL
  delivers only what is sent after).  So the refresher backs off briefly,
  builds a fresh listener, and then does a full refresh to cover whatever it
  may have missed -- including the window between process start and the
  first subscription.
- **Refresh everything, not just the named table.**  The payload names the
  affected table, but ``refresh_tables()`` re-reads all metadata anyway; a
  whole-catalog refresh is cheap relative to how rarely schemas change, and
  it handles creates, drops and renames without special cases.  The payload
  is still used for logging and for collapsing a burst of notifications into
  a single refresh.

If psycodict does not provide the notification API (any release before 1.0),
the refresher logs once and disables itself, so this module is safe to
deploy against current psycodict.
"""
import os
import threading
import time
from logging import getLogger

try:
    from psycodict.notifications import SCHEMA_CHANNEL
except ImportError:
    # psycodict without LISTEN/NOTIFY support; the refresher will disable
    # itself, but the channel name is part of psycodict's contract either way.
    SCHEMA_CHANNEL = "psycodict_schema"

logger = getLogger("lmfdb.schema_refresh")


class SchemaRefresher:
    """
    Refresh ``db``'s table metadata when a schema change is announced.

    Drive it by calling :meth:`check` regularly -- the LMFDB app does so in a
    ``before_request`` hook.  ``check`` never blocks and never raises, so it
    cannot take a request down with it.

    INPUT:

    - ``db`` -- the database whose metadata to refresh; defaults to lmfdb's
      ``db``, imported lazily so this module stays import-light
    - ``retry_interval`` -- seconds to wait before rebuilding the listener
      after a failure (default 30)
    """

    def __init__(self, db=None, retry_interval=30.0):
        self._db = db
        self.retry_interval = retry_interval
        self._listener = None
        self._pid = None
        self._next_attempt = 0.0
        self._logged_unavailable = False
        # before_request hooks may run concurrently under threaded or gevent
        # servers; one poller at a time is plenty, so extra callers just skip.
        self._lock = threading.Lock()

    @property
    def db(self):
        if self._db is None:
            from lmfdb import db
            self._db = db
        return self._db

    def available(self):
        """
        Whether psycodict provides both the notification API (``listener``)
        and the refresh API (``refresh_tables``).
        """
        return hasattr(self.db, "listener") and hasattr(self.db, "refresh_tables")

    def check(self):
        """
        Poll for schema-change notifications, refreshing metadata if any arrived.
        """
        if not self._lock.acquire(blocking=False):
            # Another thread is polling; it will see anything we would have.
            return
        try:
            self._check()
        except Exception:
            # A refresher bug must never take down the request that ran it.
            logger.exception("Unexpected error while checking for schema changes")
        finally:
            self._lock.release()

    def _check(self):
        if not self.available():
            if not self._logged_unavailable:
                logger.info(
                    "psycodict does not provide schema-change notifications; "
                    "table metadata will refresh only on restart"
                )
                self._logged_unavailable = True
            return
        if self._listener is not None and self._pid != os.getpid():
            # This process was forked (gunicorn --preload) after the listener
            # was built, so the socket is shared with the parent.  Abandon it
            # without closing -- a close would corrupt the parent's copy --
            # and build our own below.
            self._listener = None
        if self._listener is None:
            if time.monotonic() < self._next_attempt:
                return
            try:
                self._listener = self.db.listener()
                self._pid = os.getpid()
            except Exception as err:
                self._next_attempt = time.monotonic() + self.retry_interval
                logger.warning(
                    "Could not subscribe to schema-change notifications (%s); will retry", err
                )
                return
            # Notifications sent while we were not subscribed are lost, so
            # catch up with a full refresh on every (re)subscription.
            self._refresh("subscribed to schema-change notifications")
            return
        try:
            notifications = self._listener.poll()
        except Exception as err:
            self._drop_listener()
            self._next_attempt = time.monotonic() + self.retry_interval
            logger.warning("Lost the schema-change listener (%s); will resubscribe", err)
            return
        tables = sorted({payload for channel, payload in notifications if channel == SCHEMA_CHANNEL})
        if tables:
            self._refresh("schema changed for %s" % (", ".join(tables)))

    def _refresh(self, reason):
        try:
            self.db.refresh_tables()
        except Exception as err:
            # Staying subscribed with stale metadata would silently swallow
            # the failure; drop the listener so the next check resubscribes
            # and the catch-up refresh retries this one.
            self._drop_listener()
            self._next_attempt = time.monotonic() + self.retry_interval
            logger.warning("Failed to refresh table metadata (%s): %s; will retry", reason, err)
        else:
            logger.info("Refreshed table metadata: %s", reason)

    def _drop_listener(self):
        if self._listener is not None:
            try:
                self._listener.close()
            except Exception:
                pass
            self._listener = None

    def close(self):
        """
        Close the listener (if any); a later ``check`` subscribes anew.
        """
        self._drop_listener()


schema_refresher = SchemaRefresher()
