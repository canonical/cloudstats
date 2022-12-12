#!/usr/bin/python3
"""Test prometheus module."""


class TestPrometheus:
    """Prometheus test class."""

    def test_grafana_dashboard(self, prometheus):
        """Test build_dashboard function returns valid json."""

        data = prometheus.build_dashboard()
        # real dashboad data is wrapped in `dashboard`, refer to bug LP1897843
        dashboard = data.get("dashboard", {})
        assert dashboard

        # ref https://grafana.com/docs/grafana/latest/dashboards/json-model/
        json_fields = [
            # "id",  # should not exist or be None
            "uid",
            "title",
            "tags",
            "style",
            "timezone",
            "editable",
            "graphTooltip",
            "panels",
            "time",
            "timepicker",
            "templating",
            "annotations",
            # "refresh",  # not included
            "schemaVersion",
            "version",
            "links",
        ]

        for field in json_fields:
            assert field in dashboard

        assert dashboard.get("id") is None  # either non exist or None
        assert 8 <= len(dashboard["uid"]) <= 40

        assert type(dashboard["tags"]) is list
        for tag in dashboard["tags"]:
            assert type(tag) is str

        assert dashboard["style"] in ("dark", "light")
        assert dashboard["timezone"] in ("utc", "browser")
        assert type(dashboard["editable"]) is bool
        assert dashboard["graphTooltip"] in (0, 1, 2)

        assert "from" in dashboard["time"]
        assert "to" in dashboard["time"]

        timepicker_fields = [
            "collapse",
            "enable",
            "notice",
            "now",
            "refresh_intervals",
            "status",
            "type",
        ]

        for field in dashboard["timepicker"]:
            assert field in timepicker_fields

        assert "list" in dashboard["templating"]
        assert type(dashboard["templating"]["list"]) is list

        assert "list" in dashboard["annotations"]
        assert type(dashboard["annotations"]["list"]) is list

        assert type(dashboard["schemaVersion"]) is int
        assert type(dashboard["version"]) is int

        assert type(dashboard["panels"]) is list
        for panel in dashboard["panels"]:
            assert panel["id"] > 0  # positive int
            assert panel["type"]  # exist and non-empty
            assert panel["title"]
            # w and x is divided into 24 columns
            assert 1 <= panel["gridPos"]["w"] <= 24
            assert 0 <= panel["gridPos"]["x"] < 23

            # grid height units , 1 == 30 pixels
            assert 1 <= panel["gridPos"]["h"]
            assert 0 <= panel["gridPos"]["y"]
