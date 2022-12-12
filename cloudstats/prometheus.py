"""Prometheus stats processing module."""

from os.path import abspath, dirname, join

from cloudstats.config import Config
from cloudstats.logging import get_logger

import requests

import yaml


class PrometheusStats:
    """Class for interacting with Prometheus."""

    DATASOURCE = "prometheus - Juju generated source"

    def __init__(self, skip_collectors=[]):
        """Create Prometheus query interface."""
        self.logger = get_logger()
        self.config = Config().get_config("prometheus")
        self.promurl = requests.compat.urljoin(
            self.config["url"].get(str), "/api/v1/query"
        )
        self.skip_collectors = skip_collectors
        self._read_prom_query_file()
        self.dashboard_panels = []
        self.logger.debug("Configured Prometheus query interface")

    def _query_prometheus(self, query):
        """Query prometheus and catch and log errors."""
        self.logger.debug("Querying Prometheus: {}".format(query))
        try:
            response = requests.get(self.promurl, params={"query": query})
        except requests.HTTPError as e:
            self.logger.error("Prometheus returned non-200 response: {}".format(e))
            return None
        except requests.Timeout:
            self.logger.error("Prometheus query timed out.")
            return None
        except requests.exceptions.MissingSchema as e:
            self.logger.error("Prometheus URL empty or malformed: {}".format(e))
            return None
        # Process results
        try:
            results = response.json()["data"]["result"]
        except KeyError:
            self.logger.debug(
                "Unexpected response from Prometheus: {}".format(response)
            )
            return None
        self.logger.debug("Query response: {}".format(results))
        return results

    def query_prometheus_single(self, query):
        """Query Prometheus expecting a single entity and value result.

        Query is expected to return a single entity with a float or int value
        If the name of the element returns a dict with a key=value pair, the
        metric name returned will be the value.
        The name is expected to have a key=value element name and this function
        will return the value of that key, ignoring the key name.

        Example response:

        {
          "status": "success",
          "data": {
            "resultType": "vector",
            "result": [
              {
                "metric": {
                  "tenant": "admin"
                },
                "value": [
                  1601974615.112,
                  "7"
                ]
              }
            ]
          }
        }

        returns: tuple of (metric, values)
        :element:str:Value of Named of Metric queried from prometheus
        :value:int|float:Return value
        """
        results = self._query_prometheus(query)
        if not results:
            self.logger.debug("Expected one result, received none.")
            return None, None
        results = results[0]

        # process element name
        element = None
        if isinstance(results.get("metric", None), dict):
            element_data = results["metric"]
            for key in element_data.keys():
                element = element_data[key]
        else:
            element = results.get("metric", None)

        # process value, first value is float(seconds_since_epoch), second is value
        value = results.get("value", [None, "0"])[1]
        try:
            if "." in value:
                value = float(value)
            else:
                value = int(value)
        except ValueError:
            value = None

        if value is None:
            self.logger.debug(
                "Prometheus query %s did not return a readable value result: %s",
                query,
                results,
            )
        return element, value

    def _read_prom_query_file(self):
        with open(join(dirname(abspath(__file__)), "prometheus_queries.yaml")) as f:
            queries = yaml.safe_load(f)

        self.query_config = queries.pop("query_config", {})
        self.dashboard_config = queries.pop("dashboard_config", {})
        self.stats_queries = queries

    def _get_stat_query_config(self, collector, stat):
        collector_query_config = self.query_config.get(collector, {})
        return collector_query_config.get(stat, [])

    def _get_query_for_stat(self, collector, stat):
        return self.stats_queries[collector].get(stat)

    def _get_dashboard_label_for_stat(self, collector, stat):
        if collector not in self.dashboard_config["labels"]:
            return stat
        elif stat in self.dashboard_config["labels"][collector]:
            return self.dashboard_config["labels"][collector][stat]
        else:
            stat_group = "_" + "_".join(stat.split("_")[1:])
            if stat_group in self.dashboard_config["labels"][collector]:
                return "{} ({})".format(
                    self.dashboard_config["labels"][collector][stat_group],
                    stat.split("_")[0].capitalize(),
                )
        # If none of the above matches, in the labels config, stat is the label
        return stat

    def _get_dashboard_panel_grid_position(self, collector):
        default_position = {"h": 1, "w": 1, "x": 0, "y": 0}
        return self.dashboard_config.get("gridPos", {}).get(collector, default_position)

    def _get_stat(self, collector, stat):
        query_config = self._get_stat_query_config(collector, stat)
        query = self._get_query_for_stat(collector, stat)
        element, value = self.query_prometheus_single(query)
        if "result_is_element_name" in query_config:
            return element
        else:
            return value

    def get_all_stats(self):
        """Get all stats."""
        stats = {}
        for collector in self.stats_queries.keys():
            if collector in self.skip_collectors:
                continue
            for stat in self.stats_queries[collector].keys():
                result = self._get_stat(collector, stat)
                if result is None:
                    self.logger.debug(
                        "Skipping stat {}, no results retrieved.".format(stat)
                    )
                else:
                    stats[stat] = result

        return stats

    def _add_dashboard_panel(self, collector, targets):
        title = " ".join([x.capitalize() for x in collector.split("_") if x])
        self.dashboard_panels.append(
            {
                "columns": [],
                "datasource": self.DATASOURCE,
                "fontSize": "100%",
                "gridPos": self._get_dashboard_panel_grid_position(collector),
                "id": len(self.dashboard_panels) + 1,
                "title": title,
                "targets": targets,
                "styles": [{"alias": "Time", "pattern": "Time", "type": "hidden"}],
                "transform": "table",
                "transparent": True,
                "type": "table",
            }
        )

    def _get_target_template_json(self, stat, query, desc):
        data = {
            "expr": query,
            "instant": True,
            "legendFormat": desc,
            "refId": stat,
            "interval": "",
        }
        return data

    def build_dashboard(self):
        """Create dashboard json sections for prometheus_metrics.yaml data."""
        for collector in self.stats_queries.keys():
            if collector in self.skip_collectors:
                continue
            collector_stats = list(self.stats_queries[collector].keys())

            collector_targets = []
            # Determine list of panel_groups for this collector for grouping alike stats
            # stats are named min_disk_free, max_disk_free, median_disk_free, etc.
            # these stats would be all part of panel_group '_disk_free' for means of
            # sorting the targets within this collector's table.
            panel_groups = []
            for stat in collector_stats:
                stat_group = "_{}".format("_".join(stat.split("_")[1:]))
                if stat_group not in panel_groups:
                    panel_groups.append(stat_group)

            # loop through the panel_groups and add targets to the panel
            # be sure to avoid duplication that would crash grafana
            reported_stats = []
            for panel_group in panel_groups:
                # get targets, collate them, then create panel
                group_stats = [
                    stat
                    for stat in collector_stats
                    if panel_group in stat and stat not in reported_stats
                ]
                for stat in group_stats:
                    reported_stats.append(stat)
                    query = self._get_query_for_stat(collector, stat)
                    dash_label = self._get_dashboard_label_for_stat(collector, stat)
                    # add stats to targets in table
                    collector_targets.append(
                        self._get_target_template_json(stat, query, dash_label)
                    )

            # add new table
            self._add_dashboard_panel(collector, collector_targets)

        dashboard = {
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": "-- Grafana --",
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
            },
            "editable": True,
            "graphTooltip": 0,
            "iteration": 1598315651034,
            "links": [],
            "panels": self.dashboard_panels,
            "schemaVersion": 22,
            "style": "dark",
            "tags": [],
            "templating": {"list": []},
            "time": {"from": "now-15m", "to": "now"},
            "timepicker": {"collapse": True},
            "timezone": "utc",
            "title": "Cloud Capacity and Utilization",
            "variables": {"list": []},
            "version": 0,
            "uid": "94eefc30",
        }
        # have to wrap data because of bug LP1897843
        # remove this if bug fixed and all grafana charm upgraded
        return {
            "dashboard": dashboard,
            "overwrite": True,
        }
