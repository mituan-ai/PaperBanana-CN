import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

import cli


class CliEntrypointTest(unittest.TestCase):
    def test_resolve_module_script_path_finds_demo_and_viewer_modules(self):
        self.assertTrue(cli.resolve_module_script_path("demo").name.endswith("demo.py"))
        self.assertTrue(
            cli.resolve_module_script_path("visualize.show_pipeline_evolution").name.endswith(
                "show_pipeline_evolution.py"
            )
        )

    def test_help_mentions_viewer_and_standalone_install(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cli._print_help()
        help_text = buffer.getvalue()

        self.assertIn("paperbanana-pro viewer evolution", help_text)
        self.assertIn("paperbanana-pro viewer eval", help_text)
        self.assertIn("uv tool install .", help_text)
        self.assertIn("uv tool install paperbanana-pro", help_text)

    def test_main_dispatches_viewer_subcommand(self):
        with mock.patch.object(cli, "_launch_viewer", return_value=0) as launch_viewer:
            with mock.patch("sys.argv", ["paperbanana-pro", "viewer", "eval"]):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()

        self.assertEqual(ctx.exception.code, 0)
        launch_viewer.assert_called_once_with("eval", [])

    def test_main_dispatches_run_subcommand(self):
        with mock.patch.object(cli, "_launch_cli", return_value=0) as launch_cli:
            with mock.patch("sys.argv", ["paperbanana-pro", "run", "--help"]):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()

        self.assertEqual(ctx.exception.code, 0)
        launch_cli.assert_called_once_with(["--help"])


if __name__ == "__main__":
    unittest.main()
