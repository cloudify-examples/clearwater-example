########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from cloudify.decorators import operation as _operation

from chef_plugin.chef_client import run_chef

EXPECTED_OP_PREFIXES = (
    'cloudify.interfaces.lifecycle',
    'cloudify.interfaces.relationship_lifecycle')


def _extract_op(ctx):
    prefix, _, op = ctx.operation.rpartition('.')
    if prefix not in EXPECTED_OP_PREFIXES:
        ctx.logger.warn("Node operation is expected to start with '{0}' "
                        "but starts with '{1}'".format(
                            ' or '.join(EXPECTED_OP_PREFIXES), prefix))
    return op


@_operation
def operation(ctx, **kwargs):

    if 'runlist' in ctx.properties['chef_config']:
        ctx.logger.info("Using explicitly provided Chef runlist")
        runlist = ctx.properties['chef_config']['runlist']
    else:
        op = _extract_op(ctx)
        if op not in ctx.properties['chef_config']['runlists']:
            ctx.logger.warn("No Chef runlist for operation {0}".format(op))
        ctx.logger.info("Using Chef runlist for operation {0}".format(op))
        runlist = ctx.properties['chef_config']['runlists'].get(op)

    if isinstance(runlist, list):
        runlist = ','.join(runlist)

    ctx.logger.info("Chef runlist: {0}".format(runlist))
    run_chef(ctx, runlist)
