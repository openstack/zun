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
        pass

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
            NotImplementedError, self.driver.pause, self.context, mock_container
        )

    def test_unpause(self):
        pass
