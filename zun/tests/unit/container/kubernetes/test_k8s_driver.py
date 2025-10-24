from unittest import mock

from zun.container.k8s.driver import K8sDriver, zun_context
from zun.container.k8s.driver import config as k8s_config
from zun.container.k8s.network import K8sNetwork as zun_k8s_network
from zun.objects.container import Container as ZunContainer
from zun.tests.unit.container import base

FAKE_PROJECT_ID = "aaaa-bbb-ccc-ddd"


class TestK8sDriver(base.DriverTestCase):
    def setUp(self):
        super().setUp()

        # initialize/mock required config options so the driver can start...
        self.mock_admin_context = mock.patch.object(
            zun_context, "get_admin_context"
        ).start()
        self.mock_zun_k8s_network = mock.patch.object(zun_k8s_network, "init").start()
        self.mock_k8s_config = mock.patch.object(k8s_config, "load_kube_config").start()

        self.driver = K8sDriver()
        self.mock_k8s = mock.MagicMock()

        # mock calls that create may make to the k8s client
        self.mock_get_secrets_for_image = mock.patch.object(
            self.driver, "_get_secrets_for_image"
        ).start()

        self.mock_create_namespaced_deployment = mock.patch.object(
            self.driver.apps_v1, "create_namespaced_deployment"
        ).start()

        self.mock_create_namespaced_network_policy = mock.patch.object(
            self.driver.net_v1, "create_namespaced_network_policy"
        ).start()

    def test_create(self):
        """Test container create method.

        This methid implements creating a zun container object, backed by a k8s deployment.
        Returns the zun container object.
        """

        mock_image = mock.MagicMock()

        mock_container = mock.MagicMock(
            spec_set=ZunContainer,
            project_id=FAKE_PROJECT_ID,
            exposed_ports=[],
        )

        result_container = self.driver.create(
            context=self.context,
            container=mock_container,
            image=mock_image,
        )

        # some basic assertions, ensure the project ID gets passed all the way through the stack of calls

        self.assertEqual(result_container.project_id, FAKE_PROJECT_ID)

        self.mock_get_secrets_for_image.assert_called_once()
        self.mock_create_namespaced_deployment.assert_called_once()
        self.assertEqual(
            self.mock_create_namespaced_deployment.call_args[0][0], FAKE_PROJECT_ID
        )

        self.mock_create_namespaced_network_policy.assert_not_called()

    def test_create_exposedports(self):
        mock_image = mock.MagicMock()

        mock_container = mock.MagicMock(
            spec_set=ZunContainer,
            project_id=FAKE_PROJECT_ID,
            exposed_ports=["8000/tcp"],
        )

        result_container = self.driver.create(
            context=self.context,
            container=mock_container,
            image=mock_image,
        )
        self.mock_create_namespaced_network_policy.assert_called_once()
        self.assertEqual(
            self.mock_create_namespaced_network_policy.call_args[0][0], FAKE_PROJECT_ID
        )
        called_spec = self.mock_create_namespaced_network_policy.call_args[0][1]
        ingress_spec = called_spec.get("spec", {}).get("ingress", [])
        self.assertEqual(ingress_spec[0]["ports"], [{"port": 8000, "protocol": "TCP"}])

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
