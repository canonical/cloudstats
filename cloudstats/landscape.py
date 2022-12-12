"""Landscape stats processing module."""

from cloudstats.config import Config
from cloudstats.logging import get_logger

from landscape_api.base import API


class LandscapeStats:
    """Class for interacting with Landscape."""

    def __init__(self):
        """Create Landscape client."""
        self.logger = get_logger()
        self.config = Config().get_config("landscape")
        self.api = self.get_api()
        self.logger.debug("LandscapeStats initialized")

    def get_api(self):
        """Get the landscape api object."""
        uri = "https://{}/api/".format(self.config["uri"].get(str))

        api = API(
            uri,
            self.config["key"].get(str).encode("utf8"),
            self.config["secret"].get(str).encode("utf8"),
            self.config["ca"].get(str),
        )

        return api

    def get_usn_time_to_fix(self):
        """Return a repot for time to fix."""
        usn_ttf = self.api.get_usn_time_to_fix()
        self.logger.debug("USN TTF: {}".format(usn_ttf))
        return usn_ttf

    @property
    def total_machines(self):
        """The total machine count."""
        total_machines = len(self.api.get_pending_machines())
        self.logger.debug("Total machines: {}".format(total_machines))
        return total_machines

    def check_security_updates(self):
        """Return list of machines with security updates."""
        pending_machines = self.api.get_computers(query="alert:security-upgrades")

        if len(pending_machines) == 0:
            self.logger.debug("No machines have pending security upgrades.")
        else:
            self.logger.debug("Machines with pending security upgrades:")
            for computer in pending_machines:
                self.logger.debug("Id: {}".format(computer["id"]))
                self.logger.debug("Title: {}".format(computer["title"]))
                self.logger.debug("Hostname: {}".format(computer["hostname"]))
                self.logger.debug("Last ping: {}".format(computer["last_ping_time"]))

                if computer["reboot_required_flag"]:
                    self.logger.debug("Needs to reboot!")
        return pending_machines
