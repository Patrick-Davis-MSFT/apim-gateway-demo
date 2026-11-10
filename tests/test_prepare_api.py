from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError
from openapi_schema_validator import OAS30Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_api


class ImportCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "api/weather.openapi.json").read_text())

    def test_import_artifact_is_valid_reproducible_and_complete(self):
        expected, changes = prepare_api.apim_contract(self.source)
        content = (ROOT / "api/weather.apim.openapi.json").read_text()
        imported = json.loads(content)
        recorded = json.loads((ROOT / "api/inventory.json").read_text())
        self.assertEqual(imported, expected)
        validate(imported)
        self.assertEqual(imported["openapi"], "3.0.3")
        self.assertEqual(recorded["importOpenapi"], imported["openapi"])
        self.assertEqual(recorded["importSha256"], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(recorded["compatibilityChanges"], changes)
        self.assertLess(len(content), 131072)
        self.assertEqual(prepare_api.inventory(imported), prepare_api.inventory(self.source))
        self.assertEqual(len(prepare_api.inventory(imported)), 69)
        self.assertIn(
            "loadTextContent('../api/weather.apim.openapi.json')",
            (ROOT / "infra/demo.bicep").read_text(),
        )

    def test_only_version_and_nullable_types_change(self):
        original = deepcopy(self.source)
        imported, changes = prepare_api.apim_contract(self.source)
        self.assertEqual(self.source, original)
        restored = deepcopy(imported)
        restored["openapi"] = original["openapi"]
        nullable_changes = [c for c in changes if c["path"].endswith("/type")]
        self.assertEqual(sum(isinstance(c["from"], list) for c in nullable_changes), 27)
        self.assertEqual(sum(c["from"] == "null" for c in nullable_changes), 4)
        for change in nullable_changes:
            parts = change["path"].removeprefix("#/").split("/")
            node = restored
            for part in parts[:-1]:
                token = part.replace("~1", "/").replace("~0", "~")
                node = node[int(token)] if isinstance(node, list) else node[token]
            self.assertIsInstance(node["type"], str)
            self.assertTrue(node.pop("nullable"))
            if change["from"] == "null":
                self.assertEqual(node.pop("enum"), [None])
            node["type"] = change["from"]
        example_changes = [c for c in changes if c["path"].endswith("/examples")]
        self.assertEqual(len(example_changes), 13)
        for change in example_changes:
            node = restored
            for part in change["path"].removeprefix("#/").split("/")[:-1]:
                token = part.replace("~1", "/").replace("~0", "~")
                node = node[int(token)] if isinstance(node, list) else node[token]
            examples = node.pop("x-original-examples")
            self.assertEqual(examples, change["from"])
            if examples:
                self.assertEqual(node.pop("example"), examples[0])
            node["examples"] = examples
        self.assertEqual(restored, original)

    def test_null_only_branch_still_accepts_only_null(self):
        imported, _ = prepare_api.apim_contract(self.source)
        branch = imported["components"]["schemas"]["GeoJsonGeometry"]["oneOf"][-1]
        validator = OAS30Validator(branch)
        self.assertTrue(validator.is_valid(None))
        for value in ("", "value", 0, False, [], {}):
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

    def test_nested_schema_types_are_converted_but_example_data_is_preserved(self):
        self.source["components"]["schemas"]["ConversionTest"] = {
            "type": "object",
            "properties": {
                "example": {"type": ["array", "null"], "items": {"type": ["integer", "null"]}},
            },
            "additionalProperties": {"type": ["string", "null"]},
            "allOf": [{"type": ["object", "null"]}],
            "example": {"type": ["string", "null"]},
        }
        imported, _ = prepare_api.apim_contract(self.source)
        schema = imported["components"]["schemas"]["ConversionTest"]
        self.assertEqual(schema["example"], {"type": ["string", "null"]})
        self.assertEqual(schema["properties"]["example"]["type"], "array")
        self.assertTrue(schema["properties"]["example"]["items"]["nullable"])
        self.assertTrue(schema["additionalProperties"]["nullable"])
        self.assertTrue(schema["allOf"][0]["nullable"])

    def test_multiple_schema_examples_are_retained_without_modifying_example_data(self):
        examples = [{"type": ["string", "null"]}, {"type": ["number", "null"]}]
        self.source["components"]["schemas"]["ConversionTest"] = {
            "type": "object", "examples": examples,
        }
        imported, _ = prepare_api.apim_contract(self.source)
        schema = imported["components"]["schemas"]["ConversionTest"]
        self.assertEqual(schema["example"], examples[0])
        self.assertEqual(schema["x-original-examples"], examples)

    def test_unsupported_union_fails_explicitly(self):
        self.source["components"]["schemas"]["ConversionTest"] = {"type": ["string", "number", "null"]}
        with self.assertRaisesRegex(ValueError, "ConversionTest"):
            prepare_api.apim_contract(self.source)

    def test_unhandled_31_keyword_cannot_silently_enter_import(self):
        self.source["components"]["schemas"]["ConversionTest"] = {"type": "string", "const": "fixed"}
        with self.assertRaises(OpenAPIValidationError) as caught:
            prepare_api.apim_contract(self.source)
        self.assertIn("const", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
