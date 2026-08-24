import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_release import prepare_release  # noqa: E402


class PrepareReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.firmware = self.root / "application.bin"
        self.firmware.write_bytes(b"esp-idf-firmware")
        self.manifest = self.root / "manifest.json"
        self.manifest_data = {
            "protocol_version": 2,
            "product_id": 2,
            "firmware_target": "deskmate_esp32s3_v1",
            "artifacts": {
                "app": {
                    "version": "1.0.2",
                    "ota_version": 1780000000000,
                    "artifact_id": "a" * 64,
                    "file_sha256": hashlib.sha256(self.firmware.read_bytes()).hexdigest(),
                    "size": self.firmware.stat().st_size,
                }
            },
        }
        self._write_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def _write_manifest(self):
        self.manifest.write_text(json.dumps(self.manifest_data), encoding="utf-8")

    def test_packages_assets_and_adds_download_url(self):
        result = prepare_release(
            "causebefore/desksuite-firmware",
            self.firmware,
            self.manifest,
            self.root / "release",
        )

        self.assertEqual(result["tag"], "deskmate_esp32s3_v1-v1780000000000")
        firmware_asset = Path(result["firmware_asset"])
        manifest_asset = Path(result["manifest_asset"])
        self.assertEqual(firmware_asset.name, f"{'a' * 64}.bin")
        self.assertEqual(firmware_asset.read_bytes(), self.firmware.read_bytes())
        packaged = json.loads(manifest_asset.read_text(encoding="utf-8"))
        self.assertEqual(
            packaged["artifacts"]["app"]["download_url"],
            result["download_url"],
        )

    def test_rejects_firmware_digest_mismatch(self):
        self.manifest_data["artifacts"]["app"]["file_sha256"] = "b" * 64
        self._write_manifest()

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            prepare_release(
                "causebefore/desksuite-firmware",
                self.firmware,
                self.manifest,
                self.root / "release",
            )

    def test_rejects_unsafe_repository_name(self):
        with self.assertRaisesRegex(ValueError, "owner/repo"):
            prepare_release(
                "causebefore/desksuite-firmware/extra",
                self.firmware,
                self.manifest,
                self.root / "release",
            )


if __name__ == "__main__":
    unittest.main()
