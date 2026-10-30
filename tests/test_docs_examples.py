from __future__ import annotations

import re
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.agent import GENERIC_AGENT_INSTRUCTIONS
from lattice.constraints import ConstraintEngine
from lattice.parser import _CONSTRAINT_FIELDS, ValidationError, parse_model_data
from lattice.schema_text import load_json, load_yaml

# Every schema shown to users or agents must be one Lattice accepts. Checks
# each ```yaml or ```json block that defines `parameters` in the shipped skill
# files, the README and `lattice agent instructions`.
FENCED_BLOCK = re.compile(r"^```(yaml|json)\n(.*?)^```", re.M | re.S)

SOURCES = {
    str(path.relative_to(ROOT)): path.read_text()
    for path in sorted([*(ROOT / "src/lattice/resources").rglob("*.md"), *(ROOT / ".codex").rglob("*.md")])
}
SOURCES["README.md"] = (ROOT / "README.md").read_text()
SOURCES["lattice agent instructions"] = GENERIC_AGENT_INSTRUCTIONS


def schema_blocks():
    for name, text in SOURCES.items():
        for index, match in enumerate(FENCED_BLOCK.finditer(text), start=1):
            if "parameters" in match.group(2):
                yield name, index, match.group(1), match.group(2)


class DocsExamplesTests(unittest.TestCase):
    def test_finds_a_schema_in_every_skill_readme_and_the_agent_instructions(self) -> None:
        found = {name for name, _index, _language, _body in schema_blocks()}
        expected = {name for name in SOURCES if name.endswith("SKILL.md")} | {"README.md", "lattice agent instructions"}
        self.assertEqual(set(), expected - found)

    def test_agent_instructions_show_every_constraint_type(self) -> None:
        for constraint_type in _CONSTRAINT_FIELDS:
            self.assertIn(f"- type: {constraint_type}\n", GENERIC_AGENT_INSTRUCTIONS)

    def test_every_schema_example_is_valid(self) -> None:
        for name, index, language, body in schema_blocks():
            with self.subTest(source=name, block=index):
                data = load_json(body) if language == "json" else load_yaml(body)
                try:
                    model = parse_model_data(data)
                except ValidationError as error:
                    self.fail(f"{name} block {index} is not a valid schema: {' '.join(error.errors)}")
                self.assertTrue(ConstraintEngine(model).can_complete({}), f"{name} block {index} has no valid rows")


if __name__ == "__main__":
    unittest.main()
