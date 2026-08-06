import queue
import threading

import pymysql


def connect_from_env(config):
    return pymysql.connect(
        host=config["MYSQL_HOST"],
        port=int(config.get("MYSQL_PORT", 3306)),
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
        init_command="SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED",
    )


class _PooledConnection:
    """Wraps a pooled pymysql connection so `with factory() as conn:` keeps the
    same commit-on-success / rollback-on-exception contract as a raw
    pymysql.Connection, but releases the connection back to the pool on exit
    instead of leaving the socket open for garbage collection to close.
    """

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._pool._release(self._conn)
        return False


class MysqlConnectionPool:
    """A small bounded pool of reusable pymysql connections.

    Opening a MySQL connection pays a full TCP + auth handshake on every
    call; reusing connections avoids that cost on the request path once
    services run under concurrent load.
    """

    def __init__(self, config, size=10):
        self._config = config
        self._size = max(1, size)
        self._idle = queue.Queue()
        self._lock = threading.Lock()
        self._created = 0

    def _new_connection(self):
        return connect_from_env(self._config)

    def _acquire(self):
        while True:
            try:
                conn = self._idle.get_nowait()
            except queue.Empty:
                with self._lock:
                    if self._created < self._size:
                        self._created += 1
                        acquired_slot = True
                    else:
                        acquired_slot = False
                if acquired_slot:
                    try:
                        return self._new_connection()
                    except Exception:
                        with self._lock:
                            self._created -= 1
                        raise
                conn = self._idle.get()
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                with self._lock:
                    self._created -= 1

    def _release(self, conn):
        self._idle.put(conn)

    def factory(self):
        return _PooledConnection(self, self._acquire())


def build_pooled_connection_factory(config, size=10):
    return MysqlConnectionPool(config, size=size).factory
