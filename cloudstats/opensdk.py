"""Openstack stats processing module."""

import json

from cloudstats.config import Config
from cloudstats.logging import get_logger

from keystoneauth1 import exceptions as keystone_exceptions

import openstack

from prometheus_client import CollectorRegistry, Gauge


class OpenstackStats:
    """Class for interacting with Openstack."""

    def __init__(self, registry=None):
        """Create OpenStack client."""
        self.logger = get_logger()
        self.config = Config().get_config("openstack")
        self.connection = self._get_connection()
        self._clear_cache()
        self.gauge_dict = {}
        self._registry = registry or CollectorRegistry()
        self.logger.debug("OpenstackStats initialized")

    def _get_connection(self):
        """Get the connection object."""
        connection = openstack.connection.Connection(
            region_name=self.config["region_name"].get(str),
            auth=dict(
                auth_url=self.config["auth_url"].get(str),
                username=self.config["username"].get(str),
                password=self.config["password"].get(str),
            ),
            auth_type=self.config["auth_type"].get(str),
            user_domain_name=self.config["user_domain_name"].get(str),
            project_domain_name=self.config["project_domain_name"].get(str),
            identity_interface=self.config["identity_interface"].get(str),
            project_name=self.config["project_name"].get(str),
            identity_api_version=self.config["identity_api_version"].get(int),
            auth_version=self.config["auth_version"].get(int),
            cacert=self.config["cacert"].get(str),
        )

        return connection

    def _clear_cache(self):
        """Clear all cached data."""
        self._projects_cache = None
        self._hypervisors_cache = None
        self._servers_cache = None
        self._networks_cache = None
        self._subnets_cache = None
        self._ipas_cache = None
        self._routers_cache = None
        self._load_balancers_cache = None
        self._floating_ip_cache = None
        self._volumes_cache = None
        self._images_cache = None
        self._containers_cache = None

    @property
    def _projects(self):
        if not self._projects_cache:
            self._projects_cache = []
            projects_gen = self.connection.identity.projects()

            for project in projects_gen:
                self._projects_cache.append(project)

        return self._projects_cache

    @property
    def _hypervisors(self):
        if not self._hypervisors_cache:
            self._hypervisors_cache = []
            hypervisor_gen = self.connection.compute.hypervisors(details=True)

            for hypervisor in hypervisor_gen:
                self._hypervisors_cache.append(hypervisor)

        return self._hypervisors_cache

    @property
    def _servers(self):
        if not self._servers_cache:
            self._servers_cache = []
            server_gen = self.connection.compute.servers(
                details=True, all_projects=True
            )

            for server in server_gen:
                # For Ocata, pull flavor's details individually
                try:
                    if (
                        "disk" not in server["flavor"]
                        or "ephemeral" not in server["flavor"]
                    ):
                        server["flavor"] = self.connection.compute.get_flavor(
                            server["flavor"]["id"]
                        )
                except KeyError:
                    self.logger.debug(
                        "Didn't find flavor for virtual server %s, "
                        "server.flavor does not provide disk info",
                        server["id"],
                    )
                    self.keyerrorcount += 1
                self._servers_cache.append(server)

        return self._servers_cache

    @property
    def _networks(self):
        if not self._networks_cache:
            self._networks_cache = []
            network_gen = self.connection.network.networks()

            for network in network_gen:
                self._networks_cache.append(network)

        return self._networks_cache

    @property
    def _subnets(self):
        if not self._subnets_cache:
            self._subnets_cache = []
            subnets_gen = self.connection.network.subnets()

            for subnet in subnets_gen:
                self._subnets_cache.append(subnet)

        return self._subnets_cache

    @property
    def _ipas(self):
        if not self._ipas_cache:
            self._ipas_cache = []
            ipas_gen = self.connection.network.network_ip_availabilities()

            for ipa in ipas_gen:
                self._ipas_cache.append(ipa)

        return self._ipas_cache

    @property
    def _routers(self):
        if not self._routers_cache:
            self._routers_cache = []
            routers_gen = self.connection.network.routers()

            for router in routers_gen:
                self._routers_cache.append(router)

        return self._routers_cache

    @property
    def _load_balancers(self):
        if not self._load_balancers_cache:
            self._load_balancers_cache = []
            try:
                load_balancers_gen = self.connection.network.load_balancers()
                for load_balancer in load_balancers_gen:
                    self._load_balancers_cache.append(load_balancer)
            except openstack.exceptions.ResourceNotFound:
                pass

        return self._load_balancers_cache

    @property
    def _floating_ip(self):
        if not self._floating_ip_cache:
            self._floating_ip_cache = []
            floating_ip_gen = self.connection.network.ips(all_projects=True)

            for floating_ip in floating_ip_gen:
                self._floating_ip_cache.append(floating_ip)

        return self._floating_ip_cache

    @property
    def _volumes(self):
        if not self._volumes_cache:
            self._volumes_cache = []
            volumes_gen = self.connection.block_storage.volumes(all_projects=True)

            for volume in volumes_gen:
                self._volumes_cache.append(volume)

        return self._volumes_cache

    @property
    def _images(self):
        if not self._images_cache:
            self._images_cache = []
            images_gen = self.connection.image.images()

            for image in images_gen:
                self._images_cache.append(image)

        return self._images_cache

    @property
    def _containers(self):
        if not self._containers_cache:
            self._containers_cache = []
            try:
                containers_gen = self.connection.object_store.containers()

                for container in containers_gen:
                    self._containers_cache.append(container)
            except keystone_exceptions.catalog.EndpointNotFound:
                pass

        return self._containers_cache

    def get_all_stats(self):
        """Get all stats."""
        # Regen new data for all of the properties before updating gauges
        # The gauges now act as the cache
        self.keyerrorcount = 0
        self._clear_cache()
        self._get_network_stats()
        self._get_ipa_stats()
        self._get_router_stats()
        self._get_load_balancer_stats()
        self._get_volume_stats()
        self._get_image_stats()
        self._get_object_stats()
        self._get_server_stats()
        self._get_hypervisor_stats()
        if self.keyerrorcount > 0:
            self.logger.warning(
                "Experienced %s KeyErrors from opensdk that may affect metrics. "
                "More details can be found by enabling debug on cloudstats.exporter.",
                self.keyerrorcount,
            )

    def _project_id_to_name(self, id):
        """Get project name from id."""
        for project in self._projects:
            if project.id == id:
                return project.name
        return None

    def _get_object_project_name(self, object_dict):
        try:
            if object_dict["location"]["project"]["name"] is not None:
                return object_dict["location"]["project"]["name"]
            else:
                return self._project_id_to_name(object_dict["project_id"])
        except KeyError:
            self.logger.debug(
                "Key failure when looking up project_name for object %s, "
                "setting as 'unknown'",
                json.dumps(object_dict),
            )
            self.keyerrorcount += 1
            return "unknown"

    def _create_or_update_gauge(self, gauge_name, gauge_desc, labels={}, value=0.0):
        if gauge_name not in self.gauge_dict:
            self.logger.debug("Creating Gauge {}".format(gauge_name))
            if labels:
                self.gauge_dict[gauge_name] = Gauge(
                    gauge_name,
                    gauge_desc,
                    labelnames=list(labels.keys()),
                    registry=self._registry,
                )
            else:
                self.gauge_dict[gauge_name] = Gauge(
                    gauge_name,
                    gauge_desc,
                    registry=self._registry,
                )

        if labels:
            # odd difference in prometheus-client library requires calling
            # gauge set differently when you have labels
            self.logger.debug(
                "Updating Gauge {}, {}: {}".format(gauge_name, labels, value)
            )
            self.gauge_dict[gauge_name].labels(**labels).set(value)
        else:
            self.logger.debug("Updating Gauge {}: {}".format(gauge_name, value))
            self.gauge_dict[gauge_name].set(value)

    def _get_network_stats(self):
        """Get network stats."""
        self._create_or_update_gauge(
            "neutron_total_networks",
            "Total number of networks",
            value=len(self._networks),
        )

    def _get_ipa_stats(self):
        """Get network ip availability stats."""
        for ipa in self._ipas:
            for subnet in ipa.subnet_ip_availability:
                try:
                    labels = {
                        "subnet_id": subnet["subnet_id"],
                        "domain_name": ipa["location"]["project"]["domain_name"],
                        "project_name": self._get_object_project_name(ipa),
                    }
                    self._create_or_update_gauge(
                        "neutron_subnet_ips_total",
                        "total number of configured IPs in subnet",
                        labels=labels,
                        value=subnet["total_ips"],
                    )
                    self._create_or_update_gauge(
                        "neutron_subnet_ips_used",
                        "number of used IPs in subnet",
                        labels=labels,
                        value=subnet["used_ips"],
                    )
                except KeyError as e:
                    self._log_and_count_key_errors("subnet", subnet, e)

    def _get_router_stats(self):
        self._create_or_update_gauge(
            "neutron_total_routers", "Total number of routers", value=len(self._routers)
        )

    def _get_load_balancer_stats(self):
        self._create_or_update_gauge(
            "neutron_total_load_balancers",
            "Total number of load balancers",
            value=len(self._load_balancers),
        )

    def _get_volume_stats(self):
        """Get volume stats."""
        self._create_or_update_gauge(
            "cinder_total_volumes",
            "Total number of volumes in cinder",
            value=len(self._volumes),
        )

        for volume in self._volumes:
            try:
                labels = {
                    "volume_id": volume["id"],
                    "volume_backend": volume["host"],
                    "domain_name": volume["location"]["project"]["domain_name"],
                    "project_name": self._get_object_project_name(volume),
                }
                self._create_or_update_gauge(
                    "cinder_volume_size",
                    "Size of volume in cinder",
                    labels=labels,
                    value=volume["size"],
                )
            except KeyError as e:
                self._log_and_count_key_errors("volume", volume, e)

    def _get_image_stats(self):
        """Get image stats."""
        for image in self._images:
            # bypass images in pending/upload/error state with no size
            if image["size"] is None:
                continue
            try:
                labels = {
                    "image_name": image["name"],
                    "image_format": image["disk_format"],
                    "domain_name": image["location"]["project"]["domain_name"],
                    "project_name": self._get_object_project_name(image),
                }
                self._create_or_update_gauge(
                    "glance_image_size",
                    "Size of image in glance",
                    labels=labels,
                    value=image["size"],
                )
            except KeyError as e:
                self._log_and_count_key_errors("image", image, e)

    def _get_object_stats(self):
        """Get object storage stats."""
        for container in self._containers:
            labels = {"container_name": container["name"]}
            try:
                self._create_or_update_gauge(
                    "container_objects",
                    "Number of objects in container",
                    labels=labels,
                    value=container["count"],
                )
                self._create_or_update_gauge(
                    "container_bytes",
                    "Size of objects in container",
                    labels=labels,
                    value=container["bytes"],
                )
            except KeyError as e:
                self._log_and_count_key_errors("container", container, e)

    def _get_server_stats(self):
        """Get server stats."""

        def calc_local_ephemeral(server):
            try:
                return server["flavor"]["disk"] + server["flavor"]["ephemeral"]
            except KeyError:
                self.logger.debug(
                    "Could not find disk size for server %s", server["id"]
                )
                self.keyerrorcount += 1
                return 0

        for server in self._servers:
            try:
                labels = {
                    "server_uuid": server["id"],
                    "hypervisor_hostname": server["hypervisor_hostname"],
                    "domain_name": server["location"]["project"]["domain_name"],
                    "project_name": self._get_object_project_name(server),
                }
                self._create_or_update_gauge(
                    "server_ephemeral_size",
                    "Size of local storage used by server based on flavor",
                    labels=labels,
                    value=calc_local_ephemeral(server),
                )
            except KeyError as e:
                self._log_and_count_key_errors("server", server, e)

    def _get_hypervisor_stats(self):
        """Get hypervisor stats."""

        def _calc_cores(hypervisor):
            if isinstance(hypervisor["cpu_info"], str):
                hypervisor["cpu_info"] = json.loads(hypervisor["cpu_info"])
            return (
                hypervisor["cpu_info"]["topology"]["cores"]
                * hypervisor["cpu_info"]["topology"]["cells"]
            )

        hypervisors = self._hypervisors
        for hypervisor in hypervisors:
            try:
                labels = {"hypervisor_name": hypervisor["name"]}
                self._create_or_update_gauge(
                    "hypervisor_topology_n_cores",
                    "Number of physical cores on hypervisor (not HyperThreads)",
                    labels=labels,
                    value=_calc_cores(hypervisor),
                )
            except KeyError as e:
                self._log_and_count_key_errors("hypervisor", hypervisor, e)

    def _log_and_count_key_errors(self, object_type, object_dict, key_error):
        self.logger.debug(
            "Missing keys for this %s's gauges, skipping. %s: %s",
            object_type,
            json.dumps(object_dict),
            key_error,
        )
        self.keyerrorcount += 1
