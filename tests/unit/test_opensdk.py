#!/usr/bin/python3
"""Test openstack stats module."""

from keystoneauth1 import exceptions as keystone_exceptions

from openstack import exceptions as openstack_exceptions

import pytest


class TestOpenstack:
    """Openstack test class."""

    def test_pytest(self):
        """Verify pytest runs."""
        assert True

    def test_fixture(self, openstack):
        """Test if the helper fixture works."""
        assert openstack is not None
        assert openstack.config["auth_url"].get(str) == "http://127.0.0.1:5000/v3"
        assert openstack.config["password"].get(str) == "example_password"
        assert openstack.config["username"].get(str) == "admin"
        assert openstack.config["auth_type"].get(str) == "password"
        assert openstack.config["user_domain_name"].get(str) == "admin_domain"
        assert openstack.config["project_domain_name"].get(str) == "admin_domain"
        assert openstack.config["region_name"].get(str) == "example_region"
        assert openstack.config["project_name"].get(str) == "admin"
        assert openstack.config["auth_version"].get(int) == 3
        assert openstack.config["identity_api_version"].get(int) == 3

    def test_get_hypervisor_stats(self, openstack, opensdk_gauge):
        """Test get_hypervsior_stats."""
        openstack._get_hypervisor_stats()
        assert len(opensdk_gauge.args) == 1
        assert len(opensdk_gauge.kwargs) == 1
        assert len(opensdk_gauge.call_labels) == 3
        assert len(opensdk_gauge.values) == 3
        assert opensdk_gauge.args == [
            [
                "hypervisor_topology_n_cores",
                "Number of physical cores on hypervisor (not HyperThreads)",
            ],
        ]
        assert opensdk_gauge.kwargs == [{"labelnames": ["hypervisor_name"]}]
        assert opensdk_gauge.call_labels == [
            {"hypervisor_name": "mock machine 1"},
            {"hypervisor_name": "mock machine 1"},
            {"hypervisor_name": "mock machine 1"},
        ]
        assert opensdk_gauge.values == [24, 24, 24]

    def test_get_load_balancers_exception(
        self, openstack, mock_openstacksdk_connection, opensdk_gauge
    ):
        """Test exception handling on load_balancers."""
        # Raise error when collecting load_balancers
        conn = mock_openstacksdk_connection
        conn.network.load_balancers.side_effect = openstack_exceptions.ResourceNotFound
        # Verify error is being raised
        with pytest.raises(openstack_exceptions.ResourceNotFound):
            conn.network.load_balancers()
        # Verify collection completes as expected
        openstack._get_load_balancer_stats()
        assert opensdk_gauge.args == [
            ["neutron_total_load_balancers", "Total number of load balancers"],
        ]
        assert opensdk_gauge.kwargs == [{}]
        assert opensdk_gauge.call_labels == []
        assert opensdk_gauge.values == [0]

    def test_get_oject_exception(
        self, openstack, mock_openstacksdk_connection, opensdk_gauge
    ):
        """Test exception handling on object query."""
        # Raise error when collecting containers
        conn = mock_openstacksdk_connection
        conn.object_store.containers.side_effect = (
            keystone_exceptions.catalog.EndpointNotFound
        )
        # Verify error is being raised
        with pytest.raises(keystone_exceptions.catalog.EndpointNotFound):
            conn.object_store.containers()
        # Verify collection completes as expected
        openstack._get_object_stats()
        assert opensdk_gauge.args == []
        assert opensdk_gauge.kwargs == []
        assert opensdk_gauge.values == []
