# This module imports only the standard library and werkzeug, so that tests can
# load it without importing lmfdb (which connects to the database).
import os
import signal
import sys
import threading


def serve_on_main_thread_with_reloader():
    """
    Make werkzeug's reloader serve requests from the main thread.

    Werkzeug normally serves from a background thread and watches files on the
    main thread, but cypari2 only sets up a PARI stack on the main thread, so
    PARI calls from the server thread segfault.  This swaps the two roles.
    """
    import werkzeug._reloader as wr

    stock_run_with_reloader = wr.run_with_reloader

    def run_with_reloader(main_func, extra_files=None, exclude_patterns=None,
                          interval=1, reloader_type="auto"):
        # Werkzeug 2.1+ passes srv.serve_forever.  Older versions pass a closure
        # that builds the server itself, leaving no server for the watcher thread
        # to stop, so they keep werkzeug's own reloader.
        server = getattr(main_func, "__self__", None)
        if server is None:
            return stock_run_with_reloader(
                main_func, extra_files=extra_files, exclude_patterns=exclude_patterns,
                interval=interval, reloader_type=reloader_type
            )
        signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
        reloader = wr.reloader_loops[reloader_type](
            extra_files=extra_files, exclude_patterns=exclude_patterns, interval=interval
        )
        try:
            if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
                wr.ensure_echo_on()
                changed = threading.Event()

                def watch():
                    # The reloader reports a change with sys.exit(3), which only
                    # ends this thread.  Stop the server instead, so that the main
                    # thread exits with status 3 and atexit cleanup still runs.
                    try:
                        reloader.run()
                    except SystemExit:
                        changed.set()
                        server.shutdown()

                with reloader:
                    threading.Thread(target=watch, daemon=True).start()
                    main_func()
                if changed.is_set():
                    sys.exit(3)
            else:
                sys.exit(reloader.restart_with_reloader())
        except KeyboardInterrupt:
            pass

    wr.run_with_reloader = run_with_reloader
