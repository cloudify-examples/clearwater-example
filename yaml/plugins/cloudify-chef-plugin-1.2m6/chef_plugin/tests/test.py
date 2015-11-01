# *****************************************************************************
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.
# *****************************************************************************

import itertools
import os
import random
import string
import tempfile
import unittest
import logging

from cloudify import context
from cloudify import mocks

import chef_plugin.chef_client as chef_client

CHEF_CREATED_FILE_NAME = '/tmp/cloudify_plugin_chef_test.txt'
CHEF_CREATED_FILE_CONTENTS = ''.join([random.choice(
    string.ascii_uppercase + string.digits) for x in range(6)])

node_id = itertools.count(100)


def _make_context(installation_type='solo', operation=None,
                  merge_chef_attributes=None, target=None):
    props = {}
    props.setdefault('attributes', {})
    props['attributes'].setdefault('create_file', {})
    props['attributes']['create_file'].setdefault(
        'file_name', CHEF_CREATED_FILE_NAME)
    props['attributes']['create_file'].setdefault(
        'file_contents', CHEF_CREATED_FILE_CONTENTS)
    props['attributes'].update(merge_chef_attributes or {})

    ctx = mocks.MockContext({
        'blueprint': mocks.MockContext({
            'id': 'blueprint-id'
        }),
        'deployment': mocks.MockContext({
            'id': 'deployment-id'
        }),
        'operation': 'cloudify.interfaces.lifecycle.' +
                     (operation or 'INVALID'),
        'logger': logging.getLogger('test')
    })

    instance = mocks.MockContext({
        'id': 'clodufiy_app_node_id_{0}_{1}'.format(
            node_id.next(), os.getpid()),
        'runtime_properties': {}
    })

    node = mocks.MockContext({
        'name': 'clodufiy_app_node_id',
        'properties': {'chef_config': props}
    })

    if target is not None:
        ctx['source'] = mocks.MockContext({
            'instance': instance,
            'node': node
        })
        ctx['target'] = target
        ctx['type'] = context.RELATIONSHIP_INSTANCE
    else:
        ctx['instance'] = instance
        ctx['node'] = node
        ctx['type'] = context.NODE_INSTANCE
    return ctx


class MockRelatedNode(object):

    def __init__(self, node_id=None, properties=None, runtime_properties=None):
        self.node_id = node_id
        self.properties = properties
        self.runtime_properties = runtime_properties


class ChefPluginTest(object):

    def _make_context(self, operation=None, merge_chef_attributes=None):
        return _make_context(self.__class__.INSTALLATION_TYPE, operation,
                             merge_chef_attributes)


class ChefPluginAttrubutesPassingTestBase(object):

    """Tests referencing related node's runtime props as chef attrs.
    TODO: Depth tests, as opposed to only shallow tests now.
    """

    def _run(self, a1key, has_default, has_rel, has_prop_key,
             has_chef_attr_key, expect_exception=None):
        merge_chef_attributes = {
            'attr1': {
            }
        }
        merge_chef_attributes['attr1'][a1key] = 'prop1'
        if has_default:
            merge_chef_attributes['attr1'][
                'default_value'] = 'attr1_default_val'
        if has_rel:
            runtime_properties = {}
            if has_prop_key:
                runtime_properties['prop1'] = 'prop_val'
            if has_chef_attr_key:
                runtime_properties['chef_attributes'] = {
                    'prop1': 'chef_attr_val'
                }
            target = mocks.MockContext({
                'node': mocks.MockContext({
                    'properties': {}
                }),
                'instance': mocks.MockContext({
                    'id': 'clodufiy_db_node_id_' + str(node_id.next()),
                    'runtime_properties': runtime_properties
                })
            })
        else:
            target = None
        # print("MERGE_CHEF_ATTRIBUTES", merge_chef_attributes)
        ctx = _make_context(
            operation='install', merge_chef_attributes=merge_chef_attributes,
            target=target)
        # print("CTX", str(ctx), "RELATED", str(related))
        if expect_exception:
            self.assertRaises(
                expect_exception, chef_client._prepare_chef_attributes, ctx)
        else:
            return chef_client._prepare_chef_attributes(ctx)

    def test_deep(self):
        target = mocks.MockContext({
            'node': mocks.MockContext({
                'properties': {}
            }),
            'instance': mocks.MockContext({
                'id': 'clodufiy_db_node_id_' + str(node_id.next()),
                'runtime_properties': {
                    'chef_attributes': {
                        'a': {
                            'b': 7
                        }
                    }
                }
            })
        })
        ctx = _make_context(operation='install', merge_chef_attributes={
            'attr2': {
                'attr2b': {
                    'related_chef_attribute': 'a.b'
                }
            }

        }, target=target)
        # print("CTX", str(ctx), "RELATED", str(related))
        v = chef_client._prepare_chef_attributes(ctx)
        self.assertIn('attr2', v)
        self.assertIn('attr2b', v['attr2'])
        self.assertEquals(v['attr2']['attr2b'], 7)


def _make_test(h):
    def test_method(self):
        if isinstance(h[-1], type) and issubclass(h[-1], Exception):
            test_args = h
            confirmator = None
        else:
            test_args = h[:-1]
            confirmator = h[-1]
        v = self._run(*test_args)
        if confirmator:
            confirmator(self, v, "Failed for args {0}".format(test_args))
    test_method.__name__ = 'test_' + '_'.join(map(str, h[:-1]))
    return test_method


def _make_value_confirmer(expected_value):
    def f(self, v, msg):
        self.assertIn('attr1', v)
        self.assertEquals(v['attr1'], expected_value)
    f.__name__ = 'value_confirmer_{0}'.format(expected_value)
    return f


def _confirm_no_attr(self, v, msg):
    self.assertNotIn('attr1', v, msg)

_confirm_default_val = _make_value_confirmer('attr1_default_val')
_confirm_prop_val = _make_value_confirmer('prop_val')
_confirm_chef_attr_val = _make_value_confirmer('chef_attr_val')

# args:
#       a1key, has_default, has_rel, has_prop_key,
#       has_chef_attr_key, confirmator_or_excpetion
# Commented out tests without related node except for the first four of them.
# They are not interesting.
b = ChefPluginAttrubutesPassingTestBase
how = (
    ('related_runtime_property',  False,
     False,  False,  False,  _confirm_no_attr),
    ('related_chef_attribute',    False,
     False,  False,  False,  _confirm_no_attr),
    ('related_runtime_property',  True,   False,
     False,  False,  _confirm_default_val),
    ('related_chef_attribute',    True,   False,
     False,  False,  _confirm_default_val),
    ('related_runtime_property',  False,  True,   False,  False,  KeyError),
    ('related_chef_attribute',    False,  True,   False,  False,  KeyError),
    ('related_runtime_property',  True,   True,
     False,  False,  _confirm_default_val),
    ('related_chef_attribute',    True,   True,
     False,  False,  _confirm_default_val),
    # ('related_runtime_property',False,False,True,False,_confirm_no_attr),
    # ('related_chef_attribute',False,False,True,False,_confirm_no_attr),
    # ('related_runtime_property',True,False,True,False,_confirm_default_val),
    # ('related_chef_attribute',True,False,True,False,_confirm_default_val),
    ('related_runtime_property',  False,
     True,   True,   False,  _confirm_prop_val),
    ('related_chef_attribute',    False,  True,   True,   False,  KeyError),
    ('related_runtime_property',  True,   True,
     True,   False,  _confirm_prop_val),
    ('related_chef_attribute',    True,   True,
     True,   False,  _confirm_default_val),
    # ('related_runtime_property',False,False,False,True,_confirm_no_attr),
    # ('related_chef_attribute',False,False,False,True,_confirm_no_attr),
    # ('related_runtime_property',True,False,False,True,_confirm_default_val),
    # ('related_chef_attribute',True,False,False,True,_confirm_default_val),
    ('related_runtime_property',  False,  True,   False,  True,   KeyError),
    ('related_chef_attribute',    False,  True,
     False,  True,   _confirm_chef_attr_val),
    ('related_runtime_property',  True,   True,
     False,  True,   _confirm_default_val),
    ('related_chef_attribute',    True,   True,
     False,  True,   _confirm_chef_attr_val),
    # ('related_runtime_property',False,False,True,True,_confirm_no_attr),
    # ('related_chef_attribute',False,False,True,True,_confirm_no_attr),
    # ('related_runtime_property',True,False,True,True,_confirm_default_val),
    # ('related_chef_attribute',True,False,True,True,_confirm_default_val),
    ('related_runtime_property',  False,
     True,   True,   True,   _confirm_prop_val),
    ('related_chef_attribute',    False,  True,
     True,   True,   _confirm_chef_attr_val),
    ('related_runtime_property',  True,
     True,   True,   True,   _confirm_prop_val),
    ('related_chef_attribute',    True,   True,
     True,   True,   _confirm_chef_attr_val),
)

methods = {m.__name__: m for m in map(_make_test, how)}
ChefPluginAttrubutesPassingTest = type(
    'ChefPluginAttrubutesPassingTest',
    (ChefPluginTest, unittest.TestCase, b),
    methods)


class LockTest(ChefPluginTest, unittest.TestCase):

    INSTALLATION_TYPE = 'solo'

    def setUp(self):
        super(LockTest, self).setUp()
        self.path = None

    def tearDown(self):
        super(LockTest, self).tearDown()
        if self.path:
            os.remove(self.path)

    def test_clean(self):
        ctx = self._make_context()
        _, path = tempfile.mkstemp(prefix='cloudify_lock_test.')
        self.path = path
        ok = False
        try:
            with chef_client.RetryingLock(ctx, path, 3, 0.5):
                try:
                    with chef_client.RetryingLock(ctx, path, 3, 0.5):
                        pass
                except RuntimeError:
                    ok = True
        except RuntimeError:
            self.fail("Outer lock failed")
        self.assertTrue(ok, "Inner lock have not failed")


if __name__ == '__main__':
    unittest.main()
