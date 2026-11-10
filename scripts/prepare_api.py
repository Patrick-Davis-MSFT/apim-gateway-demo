"""Refresh the complete contract explicitly; never run implicitly during a demo."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import httpx2 as httpx
from openapi_spec_validator import validate

from demo import require_container

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://api.weather.gov/openapi.json"
METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def inventory(spec: dict) -> list[dict]:
    operations = []
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method in METHODS:
                operations.append({
                    "path": path, "method": method,
                    "sourceOperationId": operation["operationId"],
                    "apimOperationId": operation["operationId"],
                })
    ids = [op["apimOperationId"] for op in operations]
    if len(ids) != len(set(ids)):
        raise ValueError("Operation IDs must be unique.")
    return sorted(operations, key=lambda op: (op["path"], op["method"]))


def apim_contract(spec: dict) -> tuple[dict, list[dict]]:
    validate(spec)
    if not spec["openapi"].startswith("3.1."):
        raise ValueError("Expected an OpenAPI 3.1 Weather.gov snapshot; review compatibility before refreshing.")
    imported = deepcopy(spec)
    changes = [{"path": "#/openapi", "from": spec["openapi"], "to": "3.0.3"}]
    imported["openapi"] = "3.0.3"

    def convert(schema: dict, path: str) -> None:
        if "examples" in schema:
            if "example" in schema or "x-original-examples" in schema:
                raise ValueError(f"Conflicting schema examples at {path}")
            examples = schema.pop("examples")
            schema["x-original-examples"] = examples
            if examples:
                schema["example"] = examples[0]
            changes.append({
                "path": f"{path}/examples", "from": examples,
                "to": "example", "preservedAs": "x-original-examples",
            })
        types = schema.get("type")
        if isinstance(types, list):
            concrete = [value for value in types if value != "null"]
            if len(types) != 2 or "null" not in types or len(concrete) != 1:
                raise ValueError(f"Unsupported type union at {path}/type: {types!r}")
            schema["type"] = concrete[0]
            schema["nullable"] = True
            changes.append({
                "path": f"{path}/type", "from": types, "to": concrete[0], "nullable": True,
            })
        elif types == "null":
            if schema != {"type": "null"}:
                raise ValueError(f"Unsupported constrained null schema at {path}")
            schema.update(type="string", nullable=True, enum=[None])
            changes.append({
                "path": f"{path}/type", "from": "null", "to": "string",
                "nullable": True, "enum": [None],
            })
        for name, child in schema.get("properties", {}).items():
            token = name.replace("~", "~0").replace("/", "~1")
            convert(child, f"{path}/properties/{token}")
        for key in ("items", "additionalProperties", "not"):
            child = schema.get(key)
            if isinstance(child, dict):
                convert(child, f"{path}/{key}")
        for key in ("allOf", "anyOf", "oneOf"):
            for index, child in enumerate(schema.get(key, [])):
                convert(child, f"{path}/{key}/{index}")

    for name, schema in imported["components"]["schemas"].items():
        token = name.replace("~", "~0").replace("/", "~1")
        convert(schema, f"#/components/schemas/{token}")
    # Fail on other 3.1-only constructs rather than silently dropping them.
    validate(imported)
    return imported, changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-snapshot", action="store_true",
                        help="Regenerate the APIM import from the checked-in snapshot without downloading.")
    args = parser.parse_args()
    require_container()
    directory = ROOT / "api"
    if args.from_snapshot:
        spec = json.loads((directory / "weather.openapi.json").read_text())
    else:
        response = httpx.get(SOURCE, headers={"User-Agent": "apim-weather-walkthrough-contract-refresh"}, timeout=60)
        response.raise_for_status()
        spec = response.json()
    imported, changes = apim_contract(spec)
    operations = inventory(spec)
    directory.mkdir(exist_ok=True)
    content = json.dumps(spec, separators=(",", ":"), ensure_ascii=True) + "\n"
    import_content = json.dumps(imported, separators=(",", ":"), ensure_ascii=True) + "\n"
    (directory / "weather.openapi.json").write_text(content)
    (directory / "weather.apim.openapi.json").write_text(import_content)
    (directory / "inventory.json").write_text(json.dumps({
        "source": SOURCE, "openapi": spec["openapi"],
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "importOpenapi": imported["openapi"],
        "importSha256": hashlib.sha256(import_content.encode()).hexdigest(),
        "compatibilityChanges": changes,
        "operations": operations,
    }, indent=2) + "\n")
    print(f"Validated and saved {len(operations)} complete operations; "
          f"{len(changes)} recorded APIM compatibility changes.")


if __name__ == "__main__":
    main()
