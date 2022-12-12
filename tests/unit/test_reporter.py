#!/usr/bin/python3
"""Test cloud stats reporter daemon."""
import pytest


class TestReporterDaemon:
    """Reporter daemon test class."""

    def test_pytest(self):
        """Verify pytest runs."""
        assert True

    def test_fixture(self, reporter_daemon):
        """See if the helper fixture works to load charm configs."""
        stats_reporter_daemon = reporter_daemon()
        assert stats_reporter_daemon is not None

    def test_parse_args(self, reporter_daemon):
        """Test argument parsing."""
        # Exit on help
        with pytest.raises(SystemExit) as exit_wrapper:
            _ = reporter_daemon(("-h",))
        assert exit_wrapper.type == SystemExit

        # Default values
        statsd = reporter_daemon()
        assert statsd.config["debug"].get(bool) is False
        assert statsd.config["exporter"]["collect_interval"].get() == 15

        # User set values
        statsd = reporter_daemon(("-d", "-i", "30"))
        assert statsd.config["debug"].get(bool) is True
        assert statsd.config["exporter"]["collect_interval"].get() == 30

    def test_setup_logging(self, reporter_daemon):
        """Test setup logger."""
        statsd = reporter_daemon()
        assert statsd.config["debug"].get(bool) is False
        assert statsd.logger.getEffectiveLevel() == 20
        statsd = reporter_daemon(("-d",))
        assert statsd.config["debug"].get(bool) is True
        assert statsd.logger.getEffectiveLevel() == 10

    def test_parse_config(self, reporter_daemon):
        """Test config parsing."""
        statsd = reporter_daemon()
        assert statsd.config["debug"].get(bool) is False
        assert statsd.config["exporter"]["collect_interval"].get() == 15

    def test_run(self, reporter_daemon):
        """Test run."""
        statsd = reporter_daemon()
        statsd.trigger()
