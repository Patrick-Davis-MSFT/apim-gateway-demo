"""Run repository checks inside the DevContainer; never contact Azure."""

import json
import py_compile
import subprocess
import sys
import xml.etree.ElementTree as ET

import nbformat
from openapi_spec_validator import validate

from demo import ROOT, require_container


def main() -> None:
    require_container()
    for folder in ("scripts", "tests"):
        for file in (ROOT / folder).rglob("*.py"):
            py_compile.compile(str(file), doraise=True)
    validate(json.loads((ROOT / "api/weather.openapi.json").read_text()))
    validate(json.loads((ROOT / "api/weather.apim.openapi.json").read_text()))
    for file in (ROOT / "policies").rglob("*.xml"):
        ET.parse(file)
    notebook = nbformat.read(ROOT / "notebooks/walkthrough.ipynb", as_version=4)
    nbformat.validate(notebook)
    for template in ("main", "developer", "portal"):
        subprocess.run(
            ["az", "bicep", "build", "--file", f"infra/{template}.bicep",
             "--outfile", f"/tmp/apim-{template}.json"],
            cwd=ROOT, check=True,
        )
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    print("Local/container validation PASS. No Azure deployment or live acceptance was performed.")


if __name__ == "__main__":
    main()
