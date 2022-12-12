# CloudStats

CloudStats snap collects cloud metadata (such as total_running_vms, num_volumes, num_images, etc) and exports it via prometheus-exporter. It also provides an interface to regularly update external API with latest statistics.

This snap currently supports collecting and providing metrics for Openstack clouds. Adding supports for other clouds (e.g. Juju, Kubernetes) is in the roadmap.

For a full list of collected metrics, please refer to [cloudstats/prometheus_queries.yaml](./cloudstats/prometheus_queries.yaml).

## Deployment
To get the latest stable version of the snap from Snapstore, run:
```bash
sudo snap install cloudstats
```
To get the latest development version of the snap, build from the source code and install with `--dangerous` flag:
```bash
make build
sudo snap install --dangerous cloudstats_1.2_amd64.snap 
```

## Example usage
By default, the cloudstats uses the configuration specified in [config_default.yaml](cloudstats/config_default.yaml). It's likely not fitting your need because the values provided are generic and for demonstration purposes only. To configure cloudstats for your environment, create a `config.yaml` file in `/var/snap/cloudstats/common/` directory with the desired entries.

To start the cloudstats with the exporter and reporter services, run:
```bash
cloudstats --run-reporter --run-exporter
```
