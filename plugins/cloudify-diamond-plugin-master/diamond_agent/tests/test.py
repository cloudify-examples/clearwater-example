#########
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

import os
import mock
import unittest
import tempfile

import diamond_agent.tasks as tasks


class TestHelperFunctions(unittest.TestCase):
    @mock.patch('diamond_agent.tasks.create_paths', return_value=None)
    def test_get_paths_with_prefix(self, _):
        prefix = tempfile.mktemp()
        paths = tasks.get_paths(prefix)
        for path in paths.values():
            self.assertTrue(path.startswith(prefix))

    @mock.patch('diamond_agent.tasks.create_paths', return_value=None)
    def test_get_paths_with_env(self, _):
        prefix = tempfile.mktemp()
        with mock.patch.dict(os.environ, {'CELERY_WORK_DIR': prefix}):
            paths = tasks.get_paths(None)
        for path in paths.values():
            self.assertTrue(path.startswith(os.path.split(prefix)[0]))

    @mock.patch('diamond_agent.tasks.create_paths', return_value=None)
    def test_get_paths_without_env(self, _):
        prefix = os.path.join(tempfile.gettempdir(), 'cloudify-monitoring-')
        with mock.patch.dict(os.environ, {'CELERY_WORK_DIR': ''}):
            paths = tasks.get_paths(None)
        for path in paths.values():
            self.assertTrue(path.startswith(prefix))
