import itertools
import random
import sqlite3
import string as strings
from typing import Generator

import pytest
from _pytest.fixtures import SubRequest
from _pytest.tmpdir import TempPathFactory


@pytest.fixture(scope="session")  # type: ignore[misc]
def con() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")

    con.execute(
        """
        CREATE TABLE s (
            id INTEGER PRIMARY KEY,
            value DOUBLE PRECISION
        )
        """
    )

    con.execute(
        """
        CREATE TABLE t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )

    con.execute(
        """
        CREATE TABLE null_t (
            id INTEGER PRIMARY KEY,
            key VARCHAR(1),
            value DOUBLE PRECISION
        )
        """
    )

    rows = [
        ("a", 1.0),
        ("a", 2.0),
        ("b", 3.0),
        ("c", 4.0),
        ("c", 5.0),
    ]

    null_rows = list(
        itertools.chain(
            rows,
            [
                ("b", None),
                ("c", None),
            ],
        )
    )
    random.shuffle(null_rows)
    con.executemany("INSERT INTO null_t (key, value) VALUES (?, ?)", null_rows)
    con.executemany("INSERT INTO t (key, value) VALUES (?, ?)", rows)
    return con


@pytest.fixture(  # type: ignore[misc]
    params=[
        pytest.param(null_perc, id=null_perc_name)
        for null_perc, null_perc_name in [
            (0.0, "__0_perc_nulls"),
            (0.5, "_50_perc_nulls"),
            (1.0, "100_perc_nulls"),
        ]
    ],
    scope="session",
)
def large_con(
    request: SubRequest, tmp_path_factory: TempPathFactory
) -> Generator[sqlite3.Connection, None, None]:
    null_perc = request.param
    path = str(tmp_path_factory.mktemp("test") / "test.db")
    con = sqlite3.connect(path)
    key_n = 10
    con.execute(
        f"""
        CREATE TABLE large_t (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key INTEGER,
            dense_key INTEGER,
            string_key VARCHAR({key_n:d}),
            value DOUBLE PRECISION
        )
        """
    )

    n = int(1e5)
    rows = zip(
        (random.randrange(0, int(0.01 * n)) for _ in range(n)),
        (random.randrange(0, int(0.70 * n)) for _ in range(n)),
        (
            "".join(
                random.choices(strings.ascii_letters, k=random.randrange(0, key_n + 1))
            )
            if random.random() < (1.0 - null_perc)
            else None
            for _ in range(n)
        ),
        (random.normalvariate(0.0, 1.0) for _ in range(n)),
    )

    con.executemany(
        "INSERT INTO large_t (key, dense_key, string_key, value) VALUES (?, ?, ?, ?)",
        rows,
    )
    try:
        yield con
    finally:
        con.execute("DROP TABLE large_t")
