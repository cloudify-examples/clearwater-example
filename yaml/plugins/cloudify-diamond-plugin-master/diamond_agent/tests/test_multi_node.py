import os
import time
import cPickle
import testtools
import tempfile

from configobj import ConfigObj

from cloudify.workflows import local


class TestMultiNode(testtools.TestCase):
    def setUp(self):
        super(TestMultiNode, self).setUp()
        os.environ['MANAGEMENT_IP'] = '127.0.0.1'
        self.is_uninstallable = True
        self.env = None

    def tearDown(self):
        super(TestMultiNode, self).tearDown()
        if self.env and self.is_uninstallable:
            self.env.execute('uninstall', task_retries=0)

    def test_custom_collectors(self):
        log_path = tempfile.mktemp()
        inputs = {
            'diamond_config': {
                'prefix': tempfile.mkdtemp(prefix='cloudify-'),
                'interval': 1,
                'handlers': {
                    'test_handler.TestHandler': {
                        'path': 'handlers/test_handler.py',
                        'config': {
                            'log_path': log_path,
                        }
                    }
                }
            },
            'collectors_config': {
                'TestCollector': {
                    'path': 'collectors/test.py',
                    'config': {
                        'name': 'metric',
                        'value': 42,
                    },
                },
            },
        }
        self.env = self._create_env(inputs)
        self.env.execute('install', task_retries=0)

        if not is_created(log_path):
            self.fail('file {0} expected, but not found!'.format(log_path))

        with open(log_path, 'r') as fh:
            metric = cPickle.load(fh)
        metric_path = metric.path.split('.')

        collector_config = \
            inputs['collectors_config']['TestCollector']['config']
        self.assertEqual(collector_config['name'], metric_path[5])
        self.assertEqual(collector_config['value'], metric.value)
        self.assertEqual(self.env.name, metric_path[0])
        self.assertEqual('TestCollector', metric_path[4])

        node_instances = self.env.storage.get_node_instances()
        host_instance_id, node_id, node_instance_id = get_ids(node_instances,
                                                              'subnode')

        self.assertEqual(host_instance_id, metric_path[1])
        self.assertEqual(node_id, metric_path[2])
        self.assertEqual(node_instance_id, metric_path[3])

    def test_del_collectors(self):
        log_path = tempfile.mktemp()
        inputs = {
            'diamond_config': {
                'prefix': tempfile.mkdtemp(prefix='cloudify-'),
                'interval': 1,
                'handlers': {
                    'test_handler.TestHandler': {
                        'path': 'handlers/test_handler.py',
                        'config': {
                            'log_path': log_path,
                        }
                    }
                }
            },
            'collectors_config': {
                'TestCollector': {
                    'path': 'collectors/test.py',
                    'config': {
                        'name': 'metric',
                        'value': 42,
                    },
                },
                'CPUCollector': {
                    'config': {
                        'some': 'property',
                    },
                },
            },
        }
        self.env = self._create_env(inputs)
        self.is_uninstallable = False
        self.env.execute('install', task_retries=0)

        test_collector_conf = os.path.join(inputs['diamond_config']['prefix'],
                                           'etc', 'collectors',
                                           'TestCollector.conf')
        cpu_collector_conf = os.path.join(inputs['diamond_config']['prefix'],
                                          'etc', 'collectors',
                                          'CPUCollector.conf')

        self.assertTrue(os.path.isfile(test_collector_conf))
        self.assertEqual(ConfigObj(cpu_collector_conf)['some'], 'property')
        self.assertEqual(ConfigObj(cpu_collector_conf)['enabled'], 'True')

        # Uninstall operation is removed from blueprint so
        # the files needed for the test aren't deleted.
        # The test tests only the stop operation logic.
        self.env.execute('uninstall', task_retries=0)

        self.assertFalse(os.path.isfile(test_collector_conf))
        self.assertIsNone(ConfigObj(cpu_collector_conf).get('some'))
        self.assertEqual(ConfigObj(cpu_collector_conf)['enabled'], 'False')

    def _create_env(self, inputs):
        return local.init_env(self._blueprint_path(),
                              inputs=inputs,
                              ignored_modules=['worker_installer.tasks',
                                               'plugin_installer.tasks'])

    def _blueprint_path(self):
        return self._get_resource_path('blueprint', 'multi_node.yaml')

    def _get_resource_path(self, *args):
        return os.path.join(os.path.dirname(__file__), 'resources', *args)


def is_created(path, timeout=5):
    for _ in range(timeout):
        if os.path.isfile(path):
            return True
        time.sleep(1)
    return False


def get_ids(instances, name):
    for instance in instances:
        if instance['name'] == name:
            return instance['host_id'], instance['node_id'], instance['id']
