"""Set up cloudstats python module cli scripts."""

from setuptools import find_packages
from setuptools import setup


with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="cloudstats",
    version="0.1",
    description="Cloud metadata aggregator",
    long_description=readme,
    author="Chris Sanders",
    author_email="chris.sanders@canonical.com",
    url="https://launchpad.net/cloudstats",
    license=license,
    packages=find_packages(exclude=("tests", "docs")),
    package_data={"cloudstats": ["config_default.yaml", "prometheus_queries.yaml"]},
    entry_points={
        "console_scripts": [
            "cloudstats-exporter=cloudstats.exporter:main",
            "cloudstats-reporter=cloudstats.reporter:main",
            "cloudstats=cloudstats.cli:main",
        ]
    },
)
