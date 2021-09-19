import sqlite3

from numbsql.sqlite import sqlite3_libversion


def test_version() -> None:
    assert sqlite3_libversion() == sqlite3.sqlite_version.encode("ascii")
