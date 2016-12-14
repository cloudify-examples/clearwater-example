from cloudify import ctx
from cloudify.state import ctx_parameters as inputs

src_instance = ctx.source.instance
src_node = ctx.source.node
target_instance = ctx.target.instance
target_node = ctx.target.node

config = {}

devices_conf = config.get('devices', {})
devices_conf[target_instance.id] = device_config = {}
device_config['host_id'] = target_instance.id
device_config['node_instance_id'] = src_instance.id
device_config['node_id'] = src_node.id
if 'host' in inputs:
    device_config['host'] = inputs.host
else:
    device_config['host'] = target_instance.host_ip
device_config['port'] = inputs.port
device_config['community'] = inputs.community
device_config['oids'] = inputs.oids

config['devices'] = devices_conf

ctx.logger.info('Adding snmp collector config: {}'.format(str(config)))
src_instance.runtime_properties['snmp_config'] = config
