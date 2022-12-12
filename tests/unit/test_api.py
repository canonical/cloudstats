#!/usr/bin/python3
"""Test api module."""


class TestRestClient:
    """Landscape test class."""

    def test_pytest(self):
        """Verify pytest runs."""
        assert True

    def test_fixture(self, client):
        """Test if the helper fixture works."""
        assert client is not None
        assert client.config["url"].get(str) == "http://example.com:8000/"

    def test_setup_headers(self, client):
        """Test get_headers."""
        client._setup_headers()
        assert client._session.headers["Authorization"] == "Bearer {}".format(
            client._tokens["access"].encoded
        )

    def test_get_proxies(self, client, monkeypatch):
        """Test _get_proxies."""
        proxies = client._get_proxies()
        assert proxies == {}
        monkeypatch.setenv("HTTP_PROXY", "http://mock.proxy:3128")
        monkeypatch.setenv("HTTPS_PROXY", "https://mock.proxy:3128")
        proxies = client._get_proxies()
        assert proxies == {
            "http": "http://mock.proxy:3128",
            "https": "https://mock.proxy:3128",
        }
        monkeypatch.setenv("http_proxy", "http://mock2.proxy:3128")
        monkeypatch.setenv("https_proxy", "https://mock2.proxy:3128")
        proxies = client._get_proxies()
        assert proxies == {
            "http": "http://mock2.proxy:3128",
            "https": "https://mock2.proxy:3128",
        }
        client.config["http_proxy"].set("http://mock3.proxy:3128")
        client.config["https_proxy"].set("https://mock3.proxy:3128")
        proxies = client._get_proxies()
        assert proxies == {
            "http": "http://mock3.proxy:3128",
            "https": "https://mock3.proxy:3128",
        }

    def test_get_cloud_info(self, client):
        """Test get_cloud_info."""
        info = client.get_cloud_info(client.config["cloud_uuid"].get(str))
        assert info == {}

    def test_update_cloud_info(self, client):
        """Test update_cloud_info."""
        data = {"name": "MockName"}
        response = client.update_cloud_info(client.config["cloud_uuid"].get(str), data)
        assert response == {}
