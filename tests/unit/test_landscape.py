#!/usr/bin/python3
"""Test landscape stats module."""


class TestLandscape:
    """Landscape test class."""

    def test_pytest(self):
        """Verify pytest runs."""
        assert True

    def test_fixture(self, landscape):
        """Test if the helper fixture works."""
        assert landscape is not None
        assert landscape.config["uri"].get(str) == ""
        assert landscape.config["key"].get(str) == ""
        assert landscape.config["secret"].get(str) == ""
        assert landscape.config["ca"].get(str) == "/var/snap/cloudstats/common/ca.pem"

    def test_get_api(self, landscape, mock_landscape_api):
        """Test api loading."""
        # Defaults
        mock_landscape_api.assert_called_with(
            "https:///api/", b"", b"", "/var/snap/cloudstats/common/ca.pem"
        )

        # Check that configuration is passed in expected order
        landscape.config["uri"] = "uri"
        landscape.config["key"] = "key"
        landscape.config["secret"] = "secret"
        landscape.config["ca"] = "ca"
        _ = landscape.get_api()
        mock_landscape_api.assert_called_with(
            "https://uri/api/", b"key", b"secret", "ca"
        )

    def test_check_security_updates(self, landscape):
        """Test check security updates."""
        landscape.check_security_updates()
        landscape.api.get_computers.assert_called_with(query="alert:security-upgrades")
        assert landscape.api.get_computers.call_count == 1

        # Return a results
        test_result = {
            "id": "id",
            "title": "title",
            "hostname": "hostname",
            "last_ping_time": "last_ping_time",
            "total_memory": "total_memory",
            "reboot_required_flag": True,
        }
        landscape.api.get_computers.return_value = [test_result]
        pending = landscape.check_security_updates()
        assert landscape.api.get_computers.call_count == 2
        assert pending == [test_result]
