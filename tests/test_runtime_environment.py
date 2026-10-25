import unittest
from pathlib import Path


ADDON = Path(__file__).parents[1] / "addon" / "viesmann_dashboard"


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_python_entrypoint_is_started_with_supervisor_environment(self):
        dockerfile = (ADDON / "Dockerfile").read_text()
        run_script = (ADDON / "run.sh").read_text()

        self.assertIn('COPY run.sh /run.sh', dockerfile)
        self.assertIn('CMD ["/run.sh"]', dockerfile)
        self.assertEqual(run_script.splitlines()[0], "#!/usr/bin/with-contenv bashio")
        self.assertIn("exec python3 -m viesmann_dashboard", run_script)


if __name__ == "__main__":
    unittest.main()
