"""Main entrypoint for the cloudstats exporter daemon."""
import sys
import time

from cloudstats.config import Config
from cloudstats.logging import get_logger
from cloudstats.opensdk import OpenstackStats

from prometheus_client import CollectorRegistry, start_http_server


class StatsExporterDaemon:
    """Core class of the cloudstats exporter daemon."""

    def __init__(self, args):
        """Create new daemon and configure runtime environment."""
        self.setup_config()
        self.logger = self.setup_logging()
        self.logger.debug("Parsed config: {}".format(self.config.config_dir()))
        self._registry = CollectorRegistry()
        self.openstack = self.setup_openstack()

    def setup_config(self):
        """Parse config file as dict."""
        self.config = Config().get_config()

    def setup_logging(self):
        """Return the correct Logging instance based on debug option."""
        return get_logger(debug=self.config["debug"].get(bool))

    def setup_openstack(self):
        """Return an instance of the OpenstackStats."""
        return OpenstackStats(registry=self._registry)

    def trigger(self):
        """Configure prometheus_client gauges from generated stats."""
        self.logger.debug("Collecting gauges...")
        self.openstack.get_all_stats()
        self.logger.info("Gauges collected and ready for exporting.")

    def run(self):
        self.logger.debug("Running prometheus client http server.")
        start_http_server(
            self.config["exporter"]["port"].get(), registry=self._registry
        )
        while True:
            self.trigger()
            time.sleep(self.config["exporter"]["collect_interval"].get(int) * 60)


def main():
    """Provide the daemon entry point."""
    daemon = StatsExporterDaemon(sys.argv[1:])
    daemon.run()
