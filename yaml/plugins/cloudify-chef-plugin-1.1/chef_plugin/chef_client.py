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

"""
This module provides functions for installing, configuring and running
chef-client against an existing chef-server or chef-solo.

This module is specifically meant to be used for the cosmo celery tasks
which import the `run_chef` function.

TODO: stop passing ctx around?
"""

from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB

import copy
import re
import os
import stat
import urllib
import urlparse
import tempfile
import time
import subprocess
import json
import random

import requests

from cloudify import context


CHEF_INSTALLER_URL = "https://www.opscode.com/chef/install.sh"
SOLO_COOKBOOKS_FILE = "cookbooks.tar.gz"

ENVS_MIN_VER = [11, 8]
ENVS_MIN_VER_STR = '.'.join(map(str, ENVS_MIN_VER))

# RetryingLock() arguments: path, retries, sleep
tmp_dir = os.environ.get('TMPDIR', '/tmp')
CHEF_INSTALL_LOCK = (
    os.path.join(tmp_dir, 'cloudify-plugin-chef.install-lock'), 30, 10)  # 5min
CHEF_CLIENT_LOCK = (
    os.path.join(tmp_dir, 'cloudify-plugin-chef.client-lock'), 30, 20)  # 10min

COMMON_DIRS = {
    'checksum_path': 'checksums',
    'cookbook_path': 'cookbooks',
    'data_bag_path': 'data_bags',
    'environment_path': 'environments',
    'file_backup_path': 'backup',
    'file_cache_path': 'cache',
    'node_path': 'node',
    'role_path': 'roles',
}


class SudoError(Exception):

    """An internal exception for failures when running
    an OS command with sudo"""


class ChefError(Exception):

    """An exception for all chef related errors"""


class RetryingLock(object):

    def __init__(self, ctx, path, retries, sleep):
        self.ctx = ctx
        self.path = path
        self.retries = retries
        self.sleep = sleep
        self.acquired = False

    def __enter__(self):
        self.ctx.logger.info("Using lock file {0}".format(self.path))
        self.file = open(self.path, 'w+')
        if self.ctx.type == context.NODE_INSTANCE:
            node = self.ctx.node
            instance = self.ctx.instance
        else:
            node = self.ctx.source.node
            instance = self.ctx.source.instance
        for i in range(0, self.retries):
            try:
                flock(self.file, LOCK_EX | LOCK_NB)
            except IOError:
                self.ctx.logger.info("Could not lock the file '{0}'."
                                     "Will sleep for {1} seconds and then try "
                                     "again.".format(self.path, self.sleep))
                time.sleep(self.sleep)
            else:
                self.acquired = True
                self.ctx.logger.info("Acquired lock the file '{0}'."
                                     .format(self.path))
                self.file.truncate()
                self.file.write("worker_pid {0}\n"
                                "deployment_id {1}\n"
                                "node_name {2}\n"
                                "node_id {3}\n".format(
                                    os.getpid(),
                                    self.ctx.deployment.id,
                                    node.name,
                                    instance.id))
                self.file.flush()
                return
        raise RuntimeError("Failed to lock the file '{0}'.".format(self.path))

    def __exit__(self, exc_type, _v, _tb):
        if not self.acquired:
            return
        self.file.seek(0)
        self.file.truncate()
        self.file.write("unused\n")
        self.file.flush()
        flock(self.file, LOCK_UN)
        self.file.close()
        self.ctx.logger.info("Released lock the file '{0}'.".format(self.path))


class ChefManager(object):

    def __init__(self, ctx):
        self.ctx = ctx

    @classmethod
    def get_node_properties(cls, ctx):
        if ctx.type == context.NODE_INSTANCE:
            return ctx.node.properties
        return ctx.source.node.properties

    @classmethod
    def get_node(cls, ctx):
        if ctx.type == context.NODE_INSTANCE:
            return ctx.node
        return ctx.source.node

    @classmethod
    def get_instance(cls, ctx):
        if ctx.type == context.NODE_INSTANCE:
            return ctx.instance
        return ctx.source.instance

    @classmethod
    def can_handle(cls, ctx):
        # All of the required args exist and are not None:
        properties = cls.get_node_properties(ctx)
        return all([
                   properties['chef_config'].get(arg) is not None
                   for arg in cls.REQUIRED_ARGS
                   ])

    @classmethod
    def assert_args(cls, ctx):
        properties = cls.get_node_properties(ctx)
        missing_fields = (cls.REQUIRED_ARGS).union(
            {'version'}).difference(properties['chef_config'].keys())
        if missing_fields:
            raise ChefError(
                "The following required field(s) "
                "are missing: {0}".format(", ".join(missing_fields)))

    def get_version(self):
        """Check if chef-client is available and is of the right version"""
        binary = self._get_binary()
        if not self._prog_available_for_root(binary):
            return None

        return self._extract_chef_version(
            subprocess.check_output(["/usr/bin/sudo", binary, "--version"])
        )

    def get_chef_data_root(self):
        """ Get Chef root for this YAML node """
        # XXX: probably not fully cross-platform
        return os.path.join(os.sep, 'var', 'chef',
                            'cloudify-node-' + self.get_node(self.ctx).id)

    def get_chef_node_name(self):
        """ Get Chef's node_name for this YAML node """
        instance = self.get_instance(self.ctx)
        node_id = re.sub(
            r'[^a-zA-Z0-9-]', "-", str(instance.id))
        cc = self.get_node_properties(self.ctx)['chef_config']
        return cc['node_name_prefix'] + node_id + cc['node_name_suffix']

    def get_path(self, *p):
        """ Get absolute path to a file under Chef root """
        return os.path.join(self.get_chef_data_root(), *p)

    def install(self):
        """If needed, install chef-client and point it to the server"""
        ctx = self.ctx
        properties = self.get_node_properties(ctx)
        chef_version = properties['chef_config']['version']

        with RetryingLock(ctx, *CHEF_INSTALL_LOCK):

            current_version = self.get_version()
            if current_version:
                if current_version == self._extract_chef_version(chef_version):
                    ctx.logger.info(
                        "Chef version {0} is already installed. "
                        "Skipping installation.".format(chef_version))
                    return
                else:
                    # XXX: not tested
                    ctx.logger.info(
                        "Uninstalling Chef: requested version {0} "
                        "does not match the installed version {1}".format(
                            chef_version, current_version))
                    self.uninstall(ctx)

            ctx.logger.info('Installing Chef [chef_version=%s]', chef_version)
            chef_install_script = tempfile.NamedTemporaryFile(
                suffix="install.sh", delete=False)
            chef_install_script.close()
            try:
                urllib.urlretrieve(CHEF_INSTALLER_URL,
                                   chef_install_script.name)
                os.chmod(chef_install_script.name, stat.S_IRWXU)
                self._sudo(chef_install_script.name, "-v", chef_version)
                os.remove(chef_install_script.name)
                # on failure, leave for debugging
            except Exception as exc:
                raise ChefError("Chef install failed on:\n%s" % exc)

            ctx.logger.info('Setting up Chef [chef_server=\n%s]',
                            self.get_node_properties(ctx)['chef_config']
                            .get('chef_server_url'))

    def install_files(self):
        dirs = map(self.get_path, self.DIRS.values() + ['etc', 'log'])
        self._sudo("mkdir", "-p", *dirs)
        self._sudo("chmod", "700", self.get_chef_data_root())
        self.install_chef_handler()

    def install_chef_handler(self):
        handlers_source_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'chef', 'handler')
        handlers_destination_path = self.get_path('handler')
        self.ctx.logger.info("Installing handler {0} to {1}".format(
            handlers_source_path,
            handlers_destination_path))
        self._sudo('cp', '-r', handlers_source_path, handlers_destination_path)

    def get_chef_common_config(self):
        dirs = copy.deepcopy(self.DIRS)
        del dirs['cookbook_path']
        dirs = ['{0:20} "{1}"\n'.format(k, self.get_path(v))
                for k, v in sorted(self.DIRS.items())]
        # dirs += '{0:20} ["{1}"]\n'.format(
        #     'cookbook_path', self.DIRS['cookbook_path'])
        dirs = ''.join(dirs)
        s = (
            '# This file was generated by Cloudify Chef plugin\n'
            '# Also, Chef was installed by Cloudify Chef plugin\n' +
            '\n'
            '# *** Handler - start\n'
            'require "{0}/handler/cloudify_attributes_to_json_file.rb"\n'
            'h = Cloudify::ChefHandlers::AttributesDumpHandler.new\n'
            'start_handlers << h\n'
            'report_handlers << h\n'
            'exception_handlers << h\n'
            '# *** Handler - end\n'
            '\n'
            '# *** Paths - start\n' + dirs + '# *** Paths - end\n'
            '\n'
            'log_level              :info\n'
        ).format(self.get_chef_data_root())
        return s

    def uninstall(self):
        """Uninstall chef-client - currently only supporting apt-get"""
        # TODO: I didn't find a single method encouraged by opscode,
        #      so we need to add manually for any supported platform

        ctx = self.ctx

        def apt_platform():
            # Assuming that if apt-get exists, it's how chef was installed
            return self._prog_available_for_root('apt-get')

        if apt_platform():
            ctx.logger.info("Uninstalling old Chef via apt-get")
            try:
                self._sudo("apt-get", "remove", "--purge", "chef", "-y")
            except SudoError as exc:
                raise ChefError("chef-client uninstall failed on:\n%s" % exc)
        else:
            ctx.logger.error(
                "Chef uninstall is unimplemented for this platform, "
                "proceeding anyway")

    def run(self, runlist, chef_attributes):
        ctx = self.ctx
        self.install_files()
        self._prepare_for_run(runlist)

        t = 'cloudify_chef_attrs_in.{0}.{1}.{2}.'.format(
            self.get_node(ctx).name, self.get_instance(ctx).id, os.getpid())
        self.attribute_file = tempfile.NamedTemporaryFile(prefix=t,
                                                          suffix=".json",
                                                          delete=False)
        json.dump(chef_attributes, self.attribute_file)
        self.attribute_file.close()

        cmd = self._get_cmd(runlist)

        try:
            self._sudo(*cmd)
            os.remove(self.attribute_file.name)
            # on failure, leave for debugging
        except SudoError as exc:
            raise ChefError("The chef run failed\n"
                            "runlist: {0}\nattributes: {1}\nexception: \n{2}".
                            format(runlist, chef_attributes, exc))

    def _prepare_for_run(self, runlist):
        pass

    # Utilities from here to end of the class

    def _extract_chef_version(self, version_string):
        match = re.search(r'(\d+\.\d+\.\d+)', version_string)
        if match:
            return match.groups()[0]
        else:
            raise ChefError(
                "Failed to read chef version - '%s'" % version_string)

    def _prog_available_for_root(self, prog):
        with open(os.devnull, "w") as fnull:
            which_exitcode = subprocess.call(
                ["/usr/bin/sudo", "which", prog], stdout=fnull, stderr=fnull)
        return which_exitcode == 0

    def _log_text(self, title, prefix, text):
        ctx = self.ctx
        if not text:
            return
        ctx.logger.info('*** ' + title + ' ***')
        for line in text.splitlines():
            ctx.logger.info(prefix + line)

    def _sudo(self, *args):
        """a helper to run a subprocess with sudo, raises SudoError"""

        ctx = self.ctx

        def get_file_contents(f):
            f.flush()
            f.seek(0)
            return f.read()

        cmd = ["/usr/bin/sudo"] + list(args)
        ctx.logger.info("Running: '%s'", ' '.join(cmd))

        # TODO: Should we put the stdout/stderr in the celery logger?
        #       should we also keep output of successful runs?
        #       per log level? Also see comment under run_chef()
        stdout = tempfile.TemporaryFile('rw+b')
        stderr = tempfile.TemporaryFile('rw+b')
        out = None
        err = None
        try:
            subprocess.check_call(cmd, stdout=stdout, stderr=stderr)
            out = get_file_contents(stdout)
            err = get_file_contents(stderr)
            self._log_text("Chef stdout", "  [out] ", out)
            self._log_text("Chef stderr", "  [err] ", err)
        except subprocess.CalledProcessError as exc:
            raise SudoError("{exc}\nSTDOUT:\n{stdout}\nSTDERR:{stderr}".format(
                exc=exc,
                stdout=get_file_contents(stdout),
                stderr=get_file_contents(stderr)))
        finally:
            stdout.close()
            stderr.close()

        return out, err

    def _sudo_write_file(self, filename, contents):
        """a helper to create a file with sudo"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(contents)

        self._sudo("mv", temp_file.name, filename)


class ChefClientManager(ChefManager):

    """ Installs Chef client """

    NAME = 'client'
    REQUIRED_ARGS = {'chef_server_url', 'validation_client_name',
                     'validation_key', 'environment'}
    DIRS = {
        'cache_path': 'cache'
    }
    DIRS.update(COMMON_DIRS)

    def __init__(self, *args,  **kwargs):
        super(ChefClientManager, self).__init__(*args, **kwargs)
        ctx = self.ctx
        properties = self.get_node_properties(ctx)
        for k in 'node_name_prefix', 'node_name_suffix':
            if k not in properties['chef_config']:
                raise RuntimeError("Missing chef_config.{0} parameter".format(
                                   k))

    def _get_cmd(self, runlist):
        return [
            "chef-client",
            "-c", self.get_path('etc', 'client.rb'),
            "-o",
            runlist,
            "-j",
            self.attribute_file.name,
            "--force-formatter"]

    def _get_binary(self):
        return 'chef-client'

    def install_files(self):
        super(ChefClientManager, self).install_files()
        ctx = self.ctx
        chef_data_root = self.get_chef_data_root()
        properties = self.get_node_properties(ctx)
        if properties['chef_config'].get('validation_key'):
            self._sudo_write_file(
                self.get_path('etc', 'validation.pem'),
                properties['chef_config']['validation_key'])

        node_name = self.get_chef_node_name()
        node_name= node_name + str(random.randint(1, 10000))

        self._sudo_write_file(
            self.get_path('etc', 'client.rb'),
            self.get_chef_common_config() +
            'node_name              "{node_name}"\n'
            'ssl_verify_mode        :verify_none\n'
            'validation_client_name "{validation_client_name}"\n'
            'chef_server_url        "{chef_server_url}"\n'
            'environment            "{environment}"\n'
            'validation_key         "{chef_data_root}/etc/validation.pem"\n'
            'client_key             "{chef_data_root}/etc/client.pem"\n'
            'log_location           "{chef_data_root}/log/client.log"\n'
            'pid_file               "{chef_data_root}/client.pid"\n'
            'Chef::Log::Formatter.show_time = true\n'.format(
                node_name=node_name,
                chef_data_root=chef_data_root,
                **properties['chef_config']))


def is_resource_url(url):
    """
    Tells wether a URL is pointing to a resource (which is uploaded with
    the blueprint.
    '/xyz.tar.gz' URLs are pointing to resources.
    """
    u = urlparse.urlparse(url)
    return (not u.scheme), u.path


class ChefSoloManager(ChefManager):

    """ Installs Chef solo """

    NAME = 'solo'
    REQUIRED_ARGS = {'cookbooks'}
    DIRS = {
        'sandbox_path': 'sandbox'
    }
    DIRS.update(COMMON_DIRS)

    def _get_node_properties(self, ctx):
        if ctx.type == context.NODE_INSTANCE:
            return ctx.node.properties
        return ctx.source.node.properties

    def _url_to_dir(self, url, dst_dir):
        """
        Downloads .tar.gz from `url` and extracts to `dst_dir`.
        If URL is relative ("/xyz.tar.gz"), it's fetched using
        download_resource().
        """

        if url is None:
            return

        ctx = self.ctx

        ctx.logger.info(
            "Downloading from {0} and unpacking to {1}".format(url, dst_dir))
        temp_archive = tempfile.NamedTemporaryFile(
            suffix='.url_to_dir.tar.gz', delete=False)

        is_resource, path = is_resource_url(url)
        if is_resource:
            ctx.logger.info("Getting resource {0} to {1}".format(path,
                            temp_archive.name))
            ctx.download_resource(path, temp_archive.name)
        else:
            ctx.logger.info("Downloading from {0} to {1}".format(url,
                            temp_archive.name))
            temp_archive.write(requests.get(url).content)
            temp_archive.flush()
            temp_archive.close()

        command_list = [
            'sudo',
            'tar', '-C', dst_dir,
            '--xform', 's#^' + os.path.basename(dst_dir) + '/##',
            '-xzf', temp_archive.name]
        try:
            ctx.logger.info("Running: '%s'", ' '.join(command_list))
            subprocess.check_call(command_list)
        except subprocess.CalledProcessError as exc:
            raise ChefError("Failed to extract file {0} to directory {1} "
                            "which was downloaded from {2}. Command: {3}. "
                            "Exception: {4}".format(
                                temp_archive.name,
                                dst_dir,
                                url,
                                command_list,
                                exc))

        os.remove(temp_archive.name)  # on failure, leave for debugging
        # try:
        #     os.rmdir(os.path.join(dst_dir, os.path.basename(dst_dir)))
        # except OSError as e:
        #     if e.errno != errno.ENOENT:
        #         raise e

    def _prepare_for_run(self, runlist):
        ctx = self.ctx
        properties = self._get_node_properties(ctx)
        cc = properties['chef_config']
        file_name = self.get_path(SOLO_COOKBOOKS_FILE)
        for dl in 'environments', 'data_bags', 'roles':
            self._url_to_dir(cc.get(dl), self.get_path(dl))
        is_resource, path = is_resource_url(cc['cookbooks'])
        if is_resource:
            ctx.logger.info("Getting Chef cookbooks resource {0} to {1}"
                            .format(path, file_name))
            resource_local_file = ctx.download_resource(path)
            self._sudo("cp", resource_local_file, file_name)
            os.remove(resource_local_file)
        else:
            ctx.logger.info("Downloading Chef cookbooks from {0} to {1}"
                            .format(cc['cookbooks'], file_name))
            data = requests.get(cc['cookbooks']).content
            self._sudo_write_file(file_name, data)

    def _get_cmd(self, runlist):
        ctx = self.ctx
        cookbooks_file_path = self.get_path(SOLO_COOKBOOKS_FILE)
        cmd = ["chef-solo"]
        properties = self._get_node_properties(ctx)
        if (properties['chef_config'].get('environment', '_default')
                != '_default'):
            v = self.get_version()
            if map(int, v.split('.')) < ENVS_MIN_VER:
                raise ChefError("Chef solo environments are supported "
                                "starting at {0} but you are using {1}".
                                format(ENVS_MIN_VER_STR, v))
            cmd += ["-E", properties['chef_config']['environment']]
        cmd += [
            "-c", self.get_path('etc', 'solo.rb'),
            "-o", runlist,
            "-j", self.attribute_file.name,
            "--force-formatter",
            "-r", cookbooks_file_path
        ]
        return cmd

    def _get_binary(self):
        return 'chef-solo'

    def install_files(self):
        # Do not put 'environment' in this file.
        # It causes chef solo to act as client (than fails when certificate is
        # missing)
        super(ChefSoloManager, self).install_files()
        ctx = self.ctx
        properties = self._get_node_properties(ctx)
        self._sudo_write_file(
            self.get_path('etc', 'solo.rb'),
            self.get_chef_common_config() +
            'log_location           "{chef_data_root}/log/solo.log"\n'
            'pid_file               "{chef_data_root}/solo.pid"\n'
            'Chef::Log::Formatter.show_time = true\n'.format(
                chef_data_root=self.get_chef_data_root(),
                **properties['chef_config']))


def get_manager(ctx):
    managers = ChefClientManager, ChefSoloManager
    for cls in managers:
        if cls.can_handle(ctx):
            ctx.logger.info(
                "Chef manager class to be used: {0}".format(cls.__name__))
            cls.assert_args(ctx)
            return cls(ctx)
    arguments_sets = '; '.join(
        ['(for ' + m.NAME + '): ' + ', '.join(
            list(m.REQUIRED_ARGS)) for m in managers])
    if ctx.type == context.NODE_INSTANCE:
        chef_config = ctx.node.properties['chef_config']
    else:
        chef_config = ctx.source.node.properties['chef_config']
    raise ChefError("Failed to find appropriate Chef manager "
                    "for the specified arguments ({0}). "
                    "Possible arguments sets are: {1}"
                    .format(chef_config, arguments_sets))


def _context_to_struct(ctx, target=False):
    if target:
        ret = {
            'node_id': ctx.target.instance.id,
            'runtime_properties': ctx.target.instance.runtime_properties,
            'properties': ctx.target.node.properties,
            'blueprint_id': ctx.blueprint.id,
            'deployment_id': ctx.deployment.id,
            'capabilities': {},
        }
    else:
        if ctx.type == context.NODE_INSTANCE:
            node = ctx.node
            instance = ctx.instance
        else:
            node = ctx.source.node
            instance = ctx.source.instance
        ret = {
            'node_id': instance.id,
            'runtime_properties': instance.runtime_properties,
            'properties': node.properties,
            'blueprint_id': ctx.blueprint.id,
            'deployment_id': ctx.deployment.id,
            'capabilities': {},
        }
    if hasattr(ctx, 'capabilities'):
        ret['capabilities'] = ctx.capabilities.get_all()
    return ret


def _process_rel_runtime_props(ctx, data):
    if not isinstance(data, dict):
        return data
    ret = {}
    for k, v in data.items():
        path = None
        if isinstance(v, dict):
            if 'related_chef_attribute' in v:
                path = ['chef_attributes'] + v[
                    'related_chef_attribute'].split('.')

            if 'related_runtime_property' in v:
                path = v['related_runtime_property'].split('.')

        if path:
            # Nothing to fetch. Use default_value if provided.
            if ctx.type != context.RELATIONSHIP_INSTANCE:
                if 'default_value' in v:
                    ret[k] = v['default_value']
                continue

            ptr = ctx.target.instance.runtime_properties
            orig_path = path[:]
            try:
                while path:
                    # print("K={} V={} PATH={} PTR={}".format(k, v, path, ptr))
                    ptr = ptr[path.pop(0)]
            except KeyError:
                if 'default_value' in v:
                    ret[k] = v['default_value']
                    continue
                else:
                    raise KeyError(
                        "Runtime propery {0} not found in target "
                        "node {1}".format(
                            orig_path,
                            ctx.target.instance.runtime_properties))
            ret[k] = ptr
        else:
            ret[k] = _process_rel_runtime_props(ctx, v)
    return ret


def _prepare_chef_attributes(ctx):
    if ctx.type == context.NODE_INSTANCE:
        properties = ctx.node.properties
    else:
        properties = ctx.source.node.properties

    chef_attributes = properties['chef_config'].get('attributes', {})

    # If chef_attributes is JSON
    if isinstance(chef_attributes, basestring) and chef_attributes != '':
        try:
            chef_attributes = json.loads(chef_attributes)
        except ValueError:
            raise ChefError(
                "Failed json validation of chef chef_attributes:\n"
                "{0}".format(chef_attributes))

    if 'cloudify' in chef_attributes:
        raise ValueError("Chef attributes must not contain 'cloudify'")

    chef_attributes = chef_attributes.copy()
    chef_attributes['cloudify'] = _context_to_struct(ctx)

    if ctx.type == context.RELATIONSHIP_INSTANCE:
        chef_attributes['cloudify'][
            'related'] = _context_to_struct(ctx, target=True)

    chef_attributes = _process_rel_runtime_props(ctx, chef_attributes)

    return chef_attributes


def run_chef(ctx, runlist):
    """Run given runlist using Chef.
    ctx.node.properties.chef_config.chef_attributes can be a dict or a JSON.
    """

    if runlist is None:
        return

    chef_attributes = _prepare_chef_attributes(ctx)

    if ctx.type == context.NODE_INSTANCE:
        node = ctx.node
        instance = ctx.instance
    else:
        node = ctx.source.node
        instance = ctx.source.instance

    t = 'cloudify_chef_attrs_out.{0}.{1}.{2}.'.format(
        node.name, instance.id, os.getpid())
    attrs_tmp_file = tempfile.NamedTemporaryFile(
        prefix=t, suffix='.json', delete=False)
    chef_attributes['cloudify']['attributes_output_file'] = attrs_tmp_file.name

    ctx.logger.debug(
        "Using attributes_output_file: {0}".format(attrs_tmp_file.name))
    chef_manager = get_manager(ctx)
    chef_manager.install()
    chef_manager.run(runlist, chef_attributes)

    with open(attrs_tmp_file.name) as f:
        chef_output_attributes = json.load(f)

    del chef_output_attributes['cloudify']['runtime_properties']
    instance.runtime_properties['chef_attributes'] = chef_output_attributes

    os.remove(attrs_tmp_file.name)
