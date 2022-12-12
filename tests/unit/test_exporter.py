#!/usr/bin/python3
"""Test cloud stats exporter daemon."""


class TestExporterDaemon:
    """Exporter daemon test class."""

    def test_fixture(self, exporter_daemon):
        """See if the helper fixture works to load charm configs."""
        stats_exporter_daemon = exporter_daemon()
        assert stats_exporter_daemon is not None

    def test_setup_logging(self, exporter_daemon):
        """Test setup logger."""
        statsd = exporter_daemon()
        assert statsd.logger.getEffectiveLevel() == 20

    def test_parse_config(self, exporter_daemon):
        """Test config parsing."""
        statsd = exporter_daemon()
        assert statsd.config["debug"].get(bool) is False
        assert statsd.config["exporter"]["port"].get() == 9748
        assert statsd.config["exporter"]["collect_interval"].get() == 15

    def test_run(self, exporter_daemon):
        """Test run."""
        statsd = exporter_daemon()
        statsd.trigger()
