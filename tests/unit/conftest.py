#!/usr/bin/python3
"""Pytest fixture definitions."""

import os
import sys
from copy import copy
from datetime import datetime, timedelta

from cloudstats.api import RestClient
from cloudstats.opensdk import OpenstackStats
from cloudstats.storage import Storage

import jwt

import mock

import pytest


os.environ["CLOUDSTATSDIR"] = os.path.dirname(os.path.abspath(__file__))


def memory_storage():
    """Mock memory information."""
    return Storage(filename=":memory:")


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock requests.get."""
    mock_get = mock.Mock()
    mock_get_response = mock.Mock()
    mock_get_response.json.return_value = {}
    mock_get_response.status_code = 200
    mock_get.return_value = mock_get_response
    monkeypatch.setattr("cloudstats.api.requests.get", mock_get)

    return mock_get


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Mock requests.post."""
    access_token = jwt.encode(
        {"token_type": "access", "exp": datetime.utcnow() + timedelta(days=1)},
        "secret",
        algorithm="HS256",
    )
    refresh_token = jwt.encode(
        {"token_type": "refresh", "exp": datetime.utcnow() + timedelta(days=7)},
        "secret",
        algorithm="HS256",
    )

    mock_post = mock.Mock()
    mock_post_response = mock.Mock()
    mock_post_response.json.return_value = {
        "access": access_token,
        "refresh": refresh_token,
    }
    mock_post_response.status_code = 200
    mock_post.return_value = mock_post_response
    monkeypatch.setattr("cloudstats.api.requests.post", mock_post)

    return mock_post


@pytest.fixture
def mock_session_patch(monkeypatch):
    """Mock requests.Session.patch."""
    mock_patch = mock.Mock()
    mock_patch_response = mock.Mock()
    mock_patch_response.json.return_value = {}
    mock_patch_response.status_code = 200
    mock_patch.return_value = mock_patch_response
    monkeypatch.setattr("cloudstats.api.requests.Session.patch", mock_patch)

    return mock_patch


@pytest.fixture
def mock_landscape_api(monkeypatch):
    """Mock landscape_api module."""
    api = mock.MagicMock()
    sys.modules["landscape_api"] = mock.Mock()
    sys.modules["landscape_api.base"] = mock.Mock()
    monkeypatch.setattr("cloudstats.landscape.API", api)

    return api


def get_compute_data():
    """Mock compute return data."""
    mock_compute = mock.Mock()
    # Create hypervsior return data
    hypervisor_data = {}
    hypervisor_data["status"] = "enabled"
    hypervisor_data["state"] = "up"
    hypervisor_data["name"] = "mock machine 1"
    hypervisor_data["service_details"] = "mock service details"
    hypervisor_data["hypervisor_type"] = "QEMU"
    hypervisor_data["cpu_info"] = "mock cpu info"
    hypervisor_data["host_ip"] = "0.0.0.0"
    hypervisor_data["hypervisor_version"] = 1
    hypervisor_data["vcpus_free"] = 12
    hypervisor_data["vcpus_used"] = 12
    hypervisor_data["vcpus"] = 24
    hypervisor_data["running_vms"] = 0
    hypervisor_data["local_disk_used"] = 0
    hypervisor_data["local_disk_size"] = 50
    hypervisor_data["local_disk_free"] = 50
    hypervisor_data["memory_used"] = 512
    hypervisor_data["memory_size"] = 1024
    hypervisor_data["memory_free"] = 512
    hypervisor_data["current_workload"] = 0
    hypervisor_data["disk_available"] = 40
    cpu_info = {"topology": {"cores": 12, "cells": 2}}
    hypervisor_data["cpu_info"] = cpu_info
    hypervisor_data_list = [copy(hypervisor_data)]
    # Add a 2nd set of values to test the sum/min/mean/median calculation
    hypervisor_data["vcpus_free"] = 24
    hypervisor_data["vcpus_used"] = 24
    hypervisor_data["vcpus"] = 48
    hypervisor_data["running_vms"] = 10
    hypervisor_data["local_disk_used"] = 25
    hypervisor_data["local_disk_size"] = 100
    hypervisor_data["local_disk_free"] = 75
    hypervisor_data["memory_used"] = 1024
    hypervisor_data["memory_size"] = 2048
    hypervisor_data["memory_free"] = 1024
    hypervisor_data_list.append(copy(hypervisor_data))
    # Add a 3rd set of values so median doesn't equal mean
    hypervisor_data_list.append(copy(hypervisor_data))
    # Return data when calling hypervisors on compute
    mock_compute.hypervisors = mock.Mock()
    mock_compute.hypervisors.return_value = hypervisor_data_list
    # Mock servers call
    mock_compute.servers = mock.MagicMock()

    return mock_compute


@pytest.fixture
def mock_openstacksdk_connection(monkeypatch):
    """Mock the connection method of openstacksdk."""
    mock_connection = mock.MagicMock()
    mock_connection.return_value = mock_connection
    mock_compute = get_compute_data()
    mock_connection.compute = mock_compute
    monkeypatch.setattr(
        "cloudstats.opensdk.openstack.connection.Connection", mock_connection
    )

    return mock_connection


@pytest.fixture
def reporter_daemon(
    mock_landscape_api, mock_openstacksdk_connection, monkeypatch, client
):
    """Daemon with unit mocks applied."""
    from cloudstats.reporter import StatsReporterDaemon

    def _daemon(args=""):
        # Clear global
        monkeypatch.setattr("cloudstats.config.config", None)
        return StatsReporterDaemon(args)

    return _daemon


@pytest.fixture
def exporter_daemon(
    mock_landscape_api, mock_openstacksdk_connection, monkeypatch, client
):
    """Daemon with unit mocks applied."""
    from cloudstats.exporter import StatsExporterDaemon

    def _daemon(args=""):
        # Clear global
        monkeypatch.setattr("cloudstats.config.config", None)
        return StatsExporterDaemon(args)

    return _daemon


@pytest.fixture
def prometheus(monkeypatch):
    """Prometheus with mocks applied."""
    from cloudstats.prometheus import PrometheusStats

    prometheus = PrometheusStats()

    return prometheus


@pytest.fixture
def landscape(mock_landscape_api, monkeypatch):
    """Landscape with mocks applied."""
    from cloudstats.landscape import LandscapeStats

    landscape = LandscapeStats()

    return landscape


@pytest.fixture
def client(mock_requests_get, mock_requests_post, mock_session_patch, monkeypatch):
    """Restclient with mocks applied."""
    monkeypatch.setattr("cloudstats.api.Storage", memory_storage)
    client = RestClient()

    return client


@pytest.fixture
def openstack(mock_openstacksdk_connection, monkeypatch):
    """Openstack with mocks applied."""
    openstack = OpenstackStats()

    return openstack


@pytest.fixture
def storage(monkeypatch):
    """Storage module with mocks applied."""
    monkeypatch.setattr("cloudstats.storage.Storage", memory_storage)
    storage = memory_storage()

    return storage


@pytest.fixture
def mock_gauge():
    """Provide mechanism to test args passed in calls to prometheus_client.Gauge."""

    class TestArgs(object):
        def __init__(self):
            self.args = []
            self.kwargs = []
            self.values = []
            self.call_labels = []

        def __call__(self, *args, **kwargs):
            self.args.append(list(args))
            if "registry" in kwargs:
                kwargs.pop("registry")
            self.kwargs.append(dict(kwargs))
            return self

        def labels(self, *args, **kwargs):
            self.call_labels.append(kwargs)
            return self

        def set(self, value):
            self.values.append(value)

    return TestArgs()


@pytest.fixture
def opensdk_gauge(monkeypatch, mock_gauge):
    """Mock Gauge calls for the opensdk module path."""
    monkeypatch.setattr("cloudstats.opensdk.Gauge", mock_gauge)
    gauge = mock_gauge

    return gauge
