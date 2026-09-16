"""PostgreSQL connection helper. It performs no work until an endpoint runs."""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from identity.config import database_url


@contextmanager
def connection():
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        yield conn
