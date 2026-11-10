import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preflight


CONFIG = {
    "AZURE_ENV_NAME": "test-demo",
    "AZURE_SUBSCRIPTION_ID": "test-subscription",
    "AZURE_LOCATION": "eastus",
    "PUBLISHER_EMAIL": "publisher@example.com",
    "WEATHER_CONTACT": "weather@example.com",
    "DEMO_DEVELOPER_EMAIL": "developer@example.com",
    "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
    "AZURE_OPENAI_DEPLOYMENT": "existing-model",
}


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.values = CONFIG.copy()
        self.local = patch("preflight.local").start()
        self.environment = patch("preflight.environment", return_value=self.values).start()
        self.cli = patch(
            "preflight.cli", return_value=json.dumps({"id": CONFIG["AZURE_SUBSCRIPTION_ID"]}),
        ).start()
        self.prompt = patch("builtins.input").start()
        patch("sys.stdin.isatty", return_value=True).start()
        patch.dict(os.environ, {"AZD_NON_INTERACTIVE": "false"}).start()

    def test_strict_check_lists_all_missing_settings_with_commands(self):
        del self.values["AZURE_SUBSCRIPTION_ID"]
        del self.values["AZURE_LOCATION"]
        with self.assertRaises(RuntimeError) as caught:
            preflight.configuration()
        for name in ("AZURE_SUBSCRIPTION_ID", "AZURE_LOCATION"):
            self.assertIn(f'azd env set {name} "<value>"', str(caught.exception))
        self.prompt.assert_not_called()
        self.cli.assert_not_called()

    def test_interactive_setup_persists_missing_values(self):
        self.values.clear()
        self.values["AZURE_ENV_NAME"] = CONFIG["AZURE_ENV_NAME"]
        missing = [name for name in CONFIG if name != "AZURE_ENV_NAME"]
        self.prompt.side_effect = [CONFIG[name] for name in missing]
        preflight.configuration(interactive=True)
        self.assertEqual(self.prompt.call_count, len(missing))
        self.cli.assert_has_calls([
            call("azd", "env", "set", name, CONFIG[name]) for name in missing
        ])

    def test_existing_settings_are_not_overwritten(self):
        preflight.configuration(interactive=True)
        self.prompt.assert_not_called()
        self.cli.assert_has_calls([
            call("az", "account", "show", "--output", "json"),
            call("azd", "version"),
            call("az", "bicep", "version"),
        ])
        self.assertEqual(self.cli.call_count, 3)

    def test_placeholder_is_prompted_again(self):
        self.values["AZURE_LOCATION"] = "<region>"
        self.prompt.return_value = " eastus "
        preflight.configuration(interactive=True)
        self.cli.assert_any_call("azd", "env", "set", "AZURE_LOCATION", "eastus")

    def test_noninteractive_setup_never_prompts(self):
        del self.values["AZURE_SUBSCRIPTION_ID"]
        for noninteractive, tty in (("true", True), ("false", False)):
            with self.subTest(noninteractive=noninteractive, tty=tty):
                with patch.dict(os.environ, {"AZD_NON_INTERACTIVE": noninteractive}):
                    with patch("preflight.sys.stdin.isatty", return_value=tty):
                        with self.assertRaisesRegex(RuntimeError, "AZURE_SUBSCRIPTION_ID"):
                            preflight.configuration(interactive=True)
        self.prompt.assert_not_called()
        self.cli.assert_not_called()

    def test_invalid_input_is_not_saved(self):
        del self.values["AZURE_LOCATION"]
        for value in ("", "  ", "<region>"):
            with self.subTest(value=value):
                self.prompt.return_value = value
                with self.assertRaisesRegex(RuntimeError, "AZURE_LOCATION"):
                    preflight.configuration(interactive=True)
        self.cli.assert_not_called()

    def test_closed_input_has_actionable_error(self):
        del self.values["AZURE_SUBSCRIPTION_ID"]
        self.prompt.side_effect = EOFError
        with self.assertRaisesRegex(RuntimeError, "azd env set AZURE_SUBSCRIPTION_ID"):
            preflight.configuration(interactive=True)
        self.cli.assert_not_called()

    def test_failed_save_stops_configuration(self):
        del self.values["AZURE_LOCATION"]
        self.prompt.return_value = "eastus"
        self.cli.side_effect = RuntimeError("azd env failed")
        with self.assertRaisesRegex(RuntimeError, "azd env failed"):
            preflight.configuration(interactive=True)
        self.assertNotIn("AZURE_LOCATION", self.values)

    def test_subscription_mismatch_still_fails(self):
        self.cli.return_value = json.dumps({"id": "different-subscription"})
        with self.assertRaisesRegex(RuntimeError, "subscription differs"):
            preflight.configuration(interactive=True)

    def test_invalid_endpoint_still_fails(self):
        self.values["AZURE_OPENAI_ENDPOINT"] += "/openai"
        with self.assertRaisesRegex(ValueError, "HTTPS resource root"):
            preflight.configuration(interactive=True)


if __name__ == "__main__":
    unittest.main()
