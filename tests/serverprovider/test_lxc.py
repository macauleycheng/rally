# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import mock
import os

from rally.openstack.common import test
from rally.serverprovider.providers import lxc


class LxcContainerTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcContainerTestCase, self).setUp()
        self.server = mock.MagicMock()
        self.container = lxc.LxcContainer(self.server, {'ip': '1.2.3.4/24',
                                                        'name': 'name'})

    def test_container_construct(self):
        expected_config = {'network_bridge': 'br0', 'name': 'name',
                           'ip': '1.2.3.4/24', 'dhcp': ''}
        self.assertEqual(self.container.config, expected_config)

    def test_container_create(self):
        self.container.create('ubuntu')
        expected = [mock.call.ssh.execute('lxc-create',
                                          '-n', 'name',
                                          '-t', 'ubuntu')]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_clone(self):
        self.container.clone('src')
        expected = [mock.call.ssh.execute('lxc-clone',
                                          '-o', 'src',
                                          '-n', 'name')]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_configure(self):
        self.container.configure()
        filename = self.server.mock_calls[0][1][0]
        expected = [
            mock.call.ssh.upload(filename, '/var/lib/lxc/name/config'),
            mock.call.ssh.execute('mkdir',
                                  '/var/lib/lxc/name/rootfs/root/.ssh'),
            mock.call.ssh.execute('cp', '~/.ssh/authorized_keys',
                                  '/var/lib/lxc/name/rootfs/root/.ssh/')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_start(self):
        self.container.start()
        expected = [
            mock.call.ssh.execute('lxc-start', '-d', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_stop(self):
        self.container.stop()
        expected = [
            mock.call.ssh.execute('lxc-stop', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)

    def test_container_destroy(self):
        self.container.destroy()
        expected = [
            mock.call.ssh.execute('lxc-destroy', '-n', 'name')
        ]
        self.assertEqual(expected, self.server.mock_calls)


class FakeContainer(lxc.LxcContainer):

    def create(self, *args):
        self.status = ['created']

    def clone(self, src):
        if not hasattr(self, 'status'):
            self.status = []
        self.status.append('cloned ' + src)

    def start(self, *args):
        self.status.append('started')

    def stop(self, *args):
        self.status.append('stopped')

    def destroy(self, *args):
        self.status.append('destroyed')

    def configure(self, *args):
        self.status.append('configured')


class LxcProviderTestCase(test.BaseTestCase):

    def setUp(self):
        super(LxcProviderTestCase, self).setUp()
        self.config = {
            'name': 'LxcProvider',
            'containers_per_host': 3,
            'host_provider': {
                'name': 'DummyProvider',
                'credentials': ['root@host1.net', 'root@host2.net']}
        }
        self.provider = lxc.provider.ProviderFactory.get_provider(
            self.config, {"uuid": "fake-uuid"})

        self.h1 = mock.MagicMock()
        self.h2 = mock.MagicMock()
        self.fake_provider = mock.MagicMock()
        self.fake_provider.create_vms = mock.MagicMock(
                                            return_value=[self.h1, self.h2])

    def test_lxc_install(self):

        with mock.patch('rally.serverprovider.providers.lxc.provider') as p:
            p.ProviderFactory.get_provider =\
                mock.MagicMock(return_value=self.fake_provider)
            self.provider.lxc_install()
        expected_script = os.path.abspath('rally/serverprovider/providers/'
                                          'lxc/lxc-install.sh')
        expected = [mock.call.ssh.execute_script(expected_script)]
        self.assertEqual(expected, self.h1.mock_calls)
        self.assertEqual(expected, self.h2.mock_calls)

    def test_lxc_create_destroy_vms(self):
        mod = 'rally.serverprovider.providers.lxc.'
        with mock.patch(mod + 'provider') as p:
            p.ProviderFactory.get_provider =\
                mock.MagicMock(return_value=self.fake_provider)
            with mock.patch(mod + 'LxcContainer', new=FakeContainer):
                self.provider.create_vms()
                self.provider.destroy_vms()
        c = self.provider.containers

        name1 = c[0].config['name']
        name2 = c[3].config['name']
        ssd = ['configured', 'started', 'stopped', 'destroyed']

        self.assertEqual(c[0].status, ['created'] + ssd)
        self.assertEqual(c[1].status, ['cloned ' + name1] + ssd)
        self.assertEqual(c[2].status, ['cloned ' + name1] + ssd)

        self.assertEqual(c[3].status, ['created'] + ssd)
        self.assertEqual(c[4].status, ['cloned ' + name2] + ssd)
        self.assertEqual(c[5].status, ['cloned ' + name2] + ssd)

        self.assertEqual(len(c), 6)


class LxcProviderStaticIpTestCase(test.BaseTestCase):

    def test_static_ips(self):

        self.h1 = mock.MagicMock()
        self.h2 = mock.MagicMock()
        self.fake_provider = mock.MagicMock()
        self.fake_provider.create_vms = mock.MagicMock(
                                            return_value=[self.h1, self.h2])
        config = {
            'name': 'LxcProvider',
            'containers_per_host': 3,
            'ipv4_start_address': '1.1.1.1',
            'ipv4_prefixlen': 24,
            'host_provider': {
                'name': 'DummyProvider',
                'credentials': ['root@host1.net', 'root@host2.net']}
        }
        provider = lxc.provider.ProviderFactory.get_provider(
            config, {'uuid': 'fake-task-uuid'})

        mod = 'rally.serverprovider.providers.lxc.'
        with mock.patch(mod + 'provider') as p:
            p.ProviderFactory.get_provider =\
                mock.MagicMock(return_value=self.fake_provider)
            with mock.patch(mod + 'LxcContainer', new=FakeContainer):
                provider.create_vms()

        ips = [c.config['ip'] for c in provider.containers]
        expected = ['1.1.1.1/24', '1.1.1.2/24', '1.1.1.3/24',
                    '1.1.1.4/24', '1.1.1.5/24', '1.1.1.6/24']
        self.assertEqual(ips, expected)
