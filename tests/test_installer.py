import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


installer = load("cli_installer", "install.py")
aliases = load("k8s_aliases", "manage_k8s_aliases.py")


class InstallerTests(unittest.TestCase):
    def test_select_oc_artifact_by_architecture(self):
        files = [
            "openshift-client-linux-amd64.tar.gz",
            "openshift-client-linux-arm64.tar.gz",
            "openshift-client-linux-ppc64le.tar.gz",
        ]
        self.assertEqual(
            installer._select_oc_artifact(files, "arm64"),
            "openshift-client-linux-arm64.tar.gz",
        )

    def test_extract_checksum_for_exact_asset(self):
        checksum = "a" * 64
        content = f"{checksum}  yq_linux_amd64\n{'b' * 64}  yq_linux_arm64\n"
        self.assertEqual(installer._extract_checksum_for(content, "yq_linux_amd64"), checksum)

    def test_roxctl_latest_uses_semantic_version_order(self):
        html = '<a href="4.9.9/"></a><a href="4.10.1/"></a><a href="4.11.0/"></a>'
        with patch.object(installer, "_fetch_text", return_value=html):
            with patch.object(installer, "ROXCTL_VERSION", "latest"):
                self.assertEqual(installer._roxctl_assets_version(), "4.11.0")

    def test_ipv6_api_url(self):
        self.assertEqual(
            aliases.parse_host_port_from_url("https://[2001:db8::1]:6443"),
            ("2001:db8::1", 6443),
        )

    def test_safe_extract_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                member = tarfile.TarInfo("../escape")
                member.size = 3
                bundle.addfile(member, io.BytesIO(b"bad"))
            with self.assertRaises(RuntimeError):
                installer._safe_extract_tar_gz(archive, Path(directory) / "out")

    def test_generated_login_does_not_pass_password(self):
        config = {
            "default": "dev",
            "profiles": {
                "dev": {
                    "server": "https://api.example.test:6443",
                    "user_default": "developer",
                    "insecure": False,
                    "kubeconfig": "/tmp/config-dev",
                    "argocd_server": "argocd.example.test",
                }
            },
        }
        block = aliases.render_shell_block(config)
        self.assertIn("login --web", block)
        self.assertNotIn('-p "$pw"', block)
        self.assertNotIn('--password "$pw"', block)


if __name__ == "__main__":
    unittest.main()
