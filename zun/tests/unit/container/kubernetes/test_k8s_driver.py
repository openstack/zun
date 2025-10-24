from unittest import mock

from zun.container.k8s.driver import K8sDriver, zun_context
from zun.container.k8s.network import K8sNetwork as zun_k8s_network
from zun.tests.unit.container import base
from zun.container.k8s.driver import (
    client as k8s_client,
    config as k8s_config,
    watch as k8s_watch,
)


class TestK8sDriver(base.DriverTestCase):
    def setUp(self):
        super().setUp()

        self.mock_admin_context = mock.patch.object(
            zun_context, "get_admin_context"
        ).start()
        self.mock_zun_k8s_network = mock.patch.object(zun_k8s_network, "init").start()
        self.mock_k8s_config = mock.patch.object(k8s_config, "load_kube_config").start()

        self.driver = K8sDriver()
        self.mock_k8s = mock.MagicMock()

        # initialize/mock required config options

    def test_create(self):
        pass

    def test_commit(self):
        mock_container = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.commit,
            self.context,
            mock_container,
            repository=None,
            tag=None,
        )

    def test_delete(self):
        pass

    def test_show(self):
        pass

    def test_reboot(self):
        pass

    def test_stop(self):
        pass

    def test_start(self):
        pass

    def test_pause(self):
        mock_container = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.pause,
            self.context,
            mock_container,
        )

    def test_unpause(self):
        mock_container = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.unpause,
            self.context,
            mock_container,
        )

    def test_execute_resize(self):
        self.assertRaises(
            NotImplementedError,
            self.driver.execute_resize,
            exec_id=None,
            height=None,
            width=None,
        )

    def test_resize(self):
        mock_container = mock.MagicMock()

        fake_width = 80
        fake_height = 100

        self.assertRaises(
            NotImplementedError,
            self.driver.resize,
            self.context,
            mock_container,
            height=fake_height,
            width=fake_width,
        )

    def test_top(self):
        mock_container = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.top,
            self.context,
            mock_container,
            ps_args=None,
        )

    def test_update(self):
        mock_container = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.update,
            self.context,
            mock_container,
        )

    def test_network_detach(self):
        mock_container = mock.MagicMock()
        mock_network = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.network_detach,
            self.context,
            mock_container,
            network=mock_network,
        )

    def test_network_attach(self):
        mock_container = mock.MagicMock()
        requested_network = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.network_attach,
            self.context,
            mock_container,
            requested_network=requested_network,
        )

    def test_create_network(self):
        network = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.create_network,
            self.context,
            network=network,
        )

    def test_delete_network(self):
        network = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.delete_network,
            self.context,
            network=network,
        )

    def test_inspect_network(self):
        network = mock.MagicMock()

        self.assertRaises(
            NotImplementedError,
            self.driver.inspect_network,
            network=network,
        )
