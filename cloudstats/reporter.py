"""Main entrypoint for the cloudstats reporter daemon."""
import argparse
import sys
import time

from cloudstats.api import RestClient
from cloudstats.config import Config
from cloudstats.logging import get_logger
from cloudstats.prometheus import PrometheusStats


class StatsReporterDaemon:
    """Core class of the stats reporter daemon."""

    def __init__(self, args):
        """Create new daemon and configure runtime environment."""
        # be careful, this will change logger level
        self.prometheus = self.setup_prometheus()
        args = self.parse_args(args)
        self.config = self.parse_config(args)
        self.logger = self.setup_logging()
        self.logger.debug("Parsed config: {}".format(self.config.config_dir()))

    def setup_logging(self):
        """Return the correct Logging instance based on debug option."""
        return get_logger(debug=self.config["debug"].get(bool))

    def setup_prometheus(self):
        """Return an instance of the PrometheusStats."""
        return PrometheusStats()

    def setup_rest_client(self):
        """Return an instance of the RestClient."""
        return RestClient()

    def parse_args(self, args):
        """Parse program arguments."""
        parser = argparse.ArgumentParser(
            description="Collect and upload cloud statistics."
        )
        parser.add_argument(
            "-d", "--debug", help="Enable debug logging", action="store_true"
        )
        parser.add_argument(
            "-i",
            "--interval",
            type=int,
            dest="exporter.collect_interval",
            help="How long to wait, in minutes, between syncronisations",
        )

        return parser.parse_args(args)

    def parse_config(self, args=None):
        """Parse configuration file."""
        return Config(args).get_config()

    def collect_prometheus_data(self):
        """Get stats from prometheus."""
        stats = self.prometheus.get_all_stats()

        return stats

    def upload_data(self, data):
        """Upload collected data to api."""
        self.rest_client = self.setup_rest_client()
        self.logger.debug("Uploading data: {}".format(data))
        response = self.rest_client.update_cloud_info(
            self.config["api"]["cloud_uuid"], data
        )
        self.logger.debug("Upload Response: {}".format(response))

    def trigger(self):
        """collect data from prometheus and send to api."""
        self.logger.debug("Running reporter")
        data = self.collect_prometheus_data()
        self.logger.debug("Collected stats from Prometheus: {}".format(data))
        if self.config["api"]["url"]:
            self.upload_data(data)
        else:
            self.logger.warning("There is no API URL defined.  Exiting.")

    def run(self):
        while True:
            self.trigger()
            time.sleep(self.config["exporter"]["collect_interval"].get(int) * 60)


def main():
    """Provide the daemon entry point."""
    daemon = StatsReporterDaemon(sys.argv[1:])
    daemon.run()
