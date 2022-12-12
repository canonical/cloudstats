#!/usr/bin/env python3

import argparse
import json

from . import prometheus
from .exporter import StatsExporterDaemon
from .reporter import StatsReporterDaemon


def print_json(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def main():
    cli = argparse.ArgumentParser(
        prog="cloudstats",
        description="CloudStats CLI",
    )

    cli.add_argument(
        "-d", "--debug", dest="debug", action="store_true", help="Print debug log"
    )

    cli.add_argument(
        "--run-exporter",
        dest="run_exporter",
        action="store_true",
        help="run exporter daemon",
    )

    cli.add_argument(
        "--run-reporter",
        dest="run_reporter",
        action="store_true",
        help="run reporter daemon",
    )

    cli.add_argument(
        "--view-report",
        dest="view_report",
        action="store_true",
        help="Print report data from reporter",
    )

    cli.add_argument(
        "--update-api",
        dest="update_api",
        action="store_true",
        help="Send report data to update api/portal",
    )

    cli.add_argument(
        "--build-dashboard",
        dest="build_dashboard",
        action="store_true",
        help="Build Grafana dashboard JSON data and print",
    )

    args = cli.parse_args()
    # TODO: this is ugly, try to remove later
    daemon_args = ["-d"] if args.debug else []

    if args.view_report:
        obj = prometheus.PrometheusStats()
        data = obj.get_all_stats()
        print_json(data)
    elif args.build_dashboard:
        obj = prometheus.PrometheusStats()
        data = obj.build_dashboard()
        print_json(data)
    elif args.update_api:
        obj = StatsReporterDaemon(daemon_args)
        obj.trigger()
    elif args.run_exporter:
        obj = StatsExporterDaemon(daemon_args)
        obj.run()
    elif args.run_reporter:
        obj = StatsReporterDaemon(daemon_args)
        obj.run()


if __name__ == "__main__":
    main()
