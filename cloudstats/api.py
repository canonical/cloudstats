"""Module for interacting with Rest API."""

import urllib
from datetime import datetime, timedelta

from cloudstats.config import Config
from cloudstats.logging import get_logger
from cloudstats.storage import Storage

import jwt

import requests


class ApiError(Exception):
    """Base class for API errors."""


class AuthenticationError(ApiError):
    """Raised if authentication doesn't return a 200."""

    pass


class UpdateFailed(ApiError):
    """Raised if a patch update doesn't return 200."""

    pass


class TokenError(ApiError):
    """Raised for issues with tokens."""

    pass


class Token:
    def __init__(self, encoded):
        """Initialize Rest API Token."""
        decoded = jwt.decode(
            encoded, options=dict(verify_signature=False), algorithms="HS256"
        )
        self.encoded = encoded
        self.type = decoded["token_type"]
        self.expires = datetime.fromtimestamp(decoded["exp"])

    def __eq__(self, other):
        if self.encoded == other.encoded:
            return True

        return False

    def __gt__(self, other):
        return self.expires > other.expires

    def __ge__(self, other):
        return self.expires >= other.expires

    def __lt__(self, other):
        return self.expires < other.expires

    def __le__(self, other):
        return self.expires <= other.expires

    @property
    def is_current(self):
        """Return true if this token is current and usable."""

        target_time = datetime.utcnow() + timedelta(minutes=1)

        return self.expires > target_time

    @property
    def needs_refresh(self):
        if self.type == "access":
            target_time = datetime.utcnow()

        if self.type == "refresh":
            target_time = datetime.utcnow() + timedelta(days=5)

        return self.expires < target_time


class RestClient:
    """Class implementing a rest client."""

    def __init__(self):
        """Initialize the client."""
        self.logger = get_logger()
        self.config = Config().get_config("api")
        self._base_url = None
        self._session = None
        self._tokens = {}
        self._timeout = 5
        self._storage = Storage()
        self._setup_tokens()
        self._setup_session()

    @property
    def base_url(self):
        if self._base_url:
            return self._base_url

        base = self.config["url"].get()

        if not base.endswith("/"):
            base = base + "/"
        base = base + "api/v1/"
        self._base_url = base

        return base

    def _setup_tokens(self):
        """Load tokens."""
        # Set the refresh token
        refresh_db = self._storage.get_token("refresh")
        try:
            refresh_config_encoded = self.config["refresh_token"].get(str)
            refresh_config = Token(refresh_config_encoded)
        except jwt.exceptions.DecodeError:
            self.logger.error("Invalid refresh_token in config.")
            refresh_config = None

        # Check which exist
        valid_tokens = []

        for token in (refresh_db, refresh_config):
            if token is not None:
                valid_tokens.append(token)

        if not valid_tokens:
            raise TokenError("No refresh tokens available for API.")

        # At least one token is available
        newest_token = max(valid_tokens)

        # TODO: Do I want to error here, it will error when used anyway.
        # if not newest_token.is_current:
        #     raise TokenError("Refresh tokens have all expired.")

        self._tokens["refresh"] = newest_token

        if newest_token.needs_refresh:
            self._refresh_auth()

            return  # Nothing more to do if a refresh is required

        if newest_token == refresh_config:
            self._storage.store_token(newest_token)

        # Set the access token
        access = self._storage.get_token("access")

        if access is not None and access.is_current:
            self._tokens["access"] = access
        else:
            self._refresh_auth()

    def _setup_session(self):
        """Setup requests session."""
        self._session = requests.Session()
        self._session.timeout = self._timeout
        self._setup_headers()
        self._setup_proxies()

    def _setup_headers(self):
        """Return authenticated request headers."""
        headers = {"Authorization": "Bearer {}".format(self._tokens["access"].encoded)}
        self._session.headers.update(headers)
        self.logger.debug("Using headers: {}".format(headers))

    def _get_proxies(self):
        """Get system proxies."""
        proxies = urllib.request.getproxies()
        http_proxy = self.config["http_proxy"].get(str)
        https_proxy = self.config["https_proxy"].get(str)
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        return proxies

    def _setup_proxies(self):
        """Add proxies to session."""
        self._session.proxies = self._get_proxies()

    def _refresh_auth(self):
        """Refresh expired authentication."""
        # Using requests directly, proxies aren't set on the session yet
        proxies = self._get_proxies()
        response = requests.post(
            self.base_url + "auth/token/refresh/",
            timeout=self._timeout,
            json={"refresh": self._tokens["refresh"].encoded},
            proxies=proxies,
        )

        if response.status_code == 200:
            # Successful refresh
            data = response.json()
            access = Token(data["access"])
            refresh = Token(data["refresh"])
            self._tokens["access"] = access
            self._tokens["refresh"] = refresh
            self._storage.store_token(access)
            self._storage.store_token(refresh)

            if self._session:
                self._setup_headers()
        else:
            raise AuthenticationError(
                "Refresh failed with code: {}".format(response.status_code)
            )

    def get_cloud_info(self, cloud):
        """Return cloud information from cloud number."""

        if not self._tokens["access"].is_current:
            self._refresh_auth()
        response = self._session.patch(
            self.base_url + "clouds/{}/".format(cloud),
        )
        self.logger.debug("Cloud Info response: {}".format(response))

        if response.status_code != 200:
            raise UpdateFailed(
                "Get Info failed with code: {}".format(response.status_code)
            )

        return response.json()

    def update_cloud_info(self, cloud, data):
        """Update data on specified cloud."""

        if not self._tokens["access"].is_current:
            self._refresh_auth()
        response = self._session.patch(
            self.base_url + "clouds/{}/".format(cloud),
            json=data,
        )
        self.logger.debug("Cloud Update response: {}".format(response))

        if response.status_code != 200:
            self.logger.error(
                "Cloud Update response: {}\r reply: {}".format(
                    response.status_code, response.json()
                )
            )
            raise UpdateFailed(
                "Update failed with code: {}\r reply: {}".format(
                    response.status_code, response.json()
                )
            )

        return response.json()
