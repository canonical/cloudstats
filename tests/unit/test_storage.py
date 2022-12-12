#!/usr/bin/python3
"""Test storage module."""
from cloudstats.api import Token


class TestStorage:
    """Storage test class."""

    def test_pytest(self):
        """Verify pytest runs."""
        assert True

    def test_fixture(self, storage):
        """Test if the helper fixture works."""
        assert storage is not None

    def test_store_token(self, storage):
        """Test storing a token."""
        # the token here is used solely for example/test purposes, not in production use
        token = Token(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwidXNlcl9pZCI6MTQsImp0aSI6IjRlM2RjZWYzODcyYjE0NmI5M2txYnViNDk0Yjk2OWMwIiwiZXhwIjoxNTk2MzYyNDkxfQ.J-3QV0W4V2QUt0TETvrZUUZnV6JYWcN9I79V0Ew5sDA"  # noqa: E501
        )
        storage.store_token(token)

        token2 = storage.get_token("access")
        assert token2 == token

    def test_no_token(self, storage):
        """Test no token."""
        token = storage.get_token("access")
        assert token is None
