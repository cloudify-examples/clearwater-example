# cloudify-diamond-snmp-extension
An extension to the diamond plugin that adds support for monitoring SNMP metrics on remote machines. Here you can find an example of SNMP monitoring deployed on OpenStack.

SNMP types
----------
All node types you will need are defined in [snmp-types.yaml](snmp-types.yaml). The security group necessary for OpenStack is defined in [openstack-snmp-types.yaml](openstack-snmp-types.yaml). SNMP proxy is a node responsible for gathering the requested metrics from SNMP devices and sending them to RabbitMQ on behalf of those devices as if they were reporting those metrics by themselves (the proxy should be transparent).

### snmp_monitored_host
snmp_monitored_host exists in the blueprints only as a simulation of a monitored device. We assume that SNMP works on the device and that the SNMP proxy can access it. In our example the snmp_monitored_host is a virtual machine with Ubuntu. The snmpd_configuring_node installs SNMP daemon and changes its configuration so it can be polled from anywhere.

### snmp_proxy and snmp_manager_proxy
The nodes that poll the SNMP devices.
snmp_proxy is located  on a separate compute node and snmp_manager_proxy on the Manager.

To define the SNMP polling create a relationship for each device you want to poll. You need to add a preconfigure operation that will change the SNMPProxyCollector's configuration. In the inputs you need to specify the port (default: 161), community name (default: public) and OIDs that you wish to poll.

### snmp_security_group
 Security group that contains OpenStack rules allowing SNMP proxy to access SNMP devices.

SNMP Proxy on Manager
---------------------
[An example blueprint](proxy_on_manager.yaml)


Create a node of snmp_manager_proxy type. Next add relationships as described in snmp_proxy and snmp_manager_proxy paragraphs.

SNMP Proxy on separate VMs
--------------------------
[An example blueprint](separate_proxy.yaml)


To use a separate node you will need a Compute node with Diamond as a monitoring agent. In our example, it is the ProxyServer.
Next, create a ProxyNode contained in ProxyServer. It should be of the snmp_proxy type. Finally, add relationships as described in [_snmp_proxy and snmp_manager_proxy_](README.md#snmpproxy-and-snmpmanagerproxy).

Used scripts
------------
[append_diamond_conf.py](scripts/append_diamond_conf.py)
Adds the configuration specified in its inputs to the SNMP proxy's runtime properties so that it can be later added to the SNMPProxyCollector's config.

[install_requirements.sh](scripts/install_requirements.sh)
Installs pysnmp, python module used by the SNMPProxyCollector.

[setup_snmpd.sh](scripts/setup_snmpd.sh)
Installs the SNMP daemon and modifies its configuration so that the daemon can be polled.

Collector changes
-----------------
[snmpproxy.py](collectors/snmpproxy.py)
SNMPProxyCollector that inherits from SNMPRawCollector. The only difference is the path used to publish metric. In our implementation, it is adjusted to [cloudify-diamond-plugin](https://github.com/cloudify-cosmo/cloudify-diamond-plugin).
