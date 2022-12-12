"""Cloudstats Persistant Storage."""
import os
import sqlite3

import cloudstats.api


class StorageError(Exception):
    """Base class for storage errors."""

    pass


class TokenError(StorageError):
    """Raised if a token is not valid."""

    pass


class Storage:
    """Storage for cloudstats."""

    def __init__(self, filename=None):

        if not filename:
            filename = os.environ.get("CLOUDSTATSDIR", ".") + "/state.db"

        self._db = sqlite3.connect(str(filename), detect_types=sqlite3.PARSE_DECLTYPES)
        self._setup()

    def _setup(self):
        """Setup database"""
        # Token table
        c = self._db.execute(
            "SELECT count(name) FROM sqlite_master WHERE type='table' AND name='tokens'"
        )

        if c.fetchone()[0] == 0:
            # No table yet
            self._db.execute(
                "CREATE TABLE tokens (type TEXT, encoded TEXT, expires TIMESTAMP)"
            )

    def get_token(self, type):
        """Return the most recent tokens of the given type."""

        if type not in ("access", "refresh"):
            raise TokenError("Unknown token type: {}".format(type))

        c = self._db.execute(
            "SELECT * FROM tokens WHERE type=? ORDER BY rowid DESC LIMIT 1",
            [type],
        )
        row = c.fetchone()
        token = None

        if row:
            token = cloudstats.api.Token(row[1])

        return token

    def store_token(self, token):
        """Store token."""

        if not isinstance(token, cloudstats.api.Token):
            raise TokenError("Tokens must be of type Token.")

        self._db.execute(
            "INSERT into tokens VALUES (?,?,?)",
            [token.type, token.encoded, token.expires],
        )
        # Keep only the newest 10 tokens of this type
        self._db.execute(
            (
                "DELETE FROM tokens WHERE type=? AND rowid IN "
                "(SELECT rowid FROM tokens ORDER BY rowid DESC LIMIT -1 OFFSET 10)"
            ),
            [token.type],
        )
        self._db.commit()
