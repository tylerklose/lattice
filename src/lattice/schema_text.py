"""Read schema text (JSON or YAML) into plain dicts, lists and strings.

Every value keeps the text the user wrote. `1.10` stays "1.10", `0x1F` stays
"0x1F" and `2026-10-26T10:00:00Z` stays as typed, instead of being converted to
a number or datetime and printed back differently by Python and Ruby. The only
conversions:

- unquoted yes/no/on/off/true/false (in the case forms below) become
  True/False, and an empty value, ~ or null becomes None;
- JSON integers are written in plain decimal form.

The Ruby implementation (Lattice::SchemaText) follows the same rules, and
tests/fixtures/scalar_text.* pins the result for both.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from lattice.model import normalize_scalar

TRUE_WORDS = frozenset({"yes", "Yes", "YES", "true", "True", "TRUE", "on", "On", "ON"})
FALSE_WORDS = frozenset({"no", "No", "NO", "false", "False", "FALSE", "off", "Off", "OFF"})
NULL_WORDS = frozenset({"", "~", "null", "Null", "NULL"})

YAML_TAG_PREFIX = "tag:yaml.org,2002:"
STR_TAG = YAML_TAG_PREFIX + "str"
MERGE_TAG = YAML_TAG_PREFIX + "merge"
SCALAR_TAGS = frozenset(
    YAML_TAG_PREFIX + name for name in ("str", "int", "float", "bool", "null", "timestamp", "binary", "merge", "value")
)
SEQUENCE_TAG = YAML_TAG_PREFIX + "seq"
MAPPING_TAG = YAML_TAG_PREFIX + "map"


class SchemaSyntaxError(ValueError):
    """Raised when schema text uses YAML or JSON the schema format doesn't accept."""


MAX_VALUES = 100_000
TOO_LARGE = f"schema expands to more than {MAX_VALUES} values (check YAML aliases)"


class SchemaTooLarge(ValueError):
    """Raised when YAML aliases would expand the schema past MAX_VALUES values
    (the "billion laughs" pattern). Every value counts once per place it appears
    after expansion, so the limit holds however the aliases nest."""


class _Expansion:
    """Nodes being built (to catch recursive aliases), finished anchored nodes
    as id -> (value, size), and the running count of expanded values."""

    def __init__(self) -> None:
        self.building: set[int] = set()
        self.built: dict[int, tuple[Any, int]] = {}
        self.count = 0

    def add(self, values: int) -> None:
        self.count += values
        if self.count > MAX_VALUES:
            raise SchemaTooLarge(TOO_LARGE)


class _Loader(yaml.SafeLoader):
    """Marks scalars tagged with the bare `!` as strings, as the YAML spec (and
    Ruby's Psych) do; PyYAML would otherwise resolve `! true` like `true`."""

    def compose_scalar_node(self, anchor: Any) -> ScalarNode:
        explicit_string = self.peek_event().tag == "!"
        node = super().compose_scalar_node(anchor)
        if explicit_string:
            node.tag = STR_TAG
        return node


def load_json(text: str) -> Any:
    return json.loads(
        text,
        parse_float=str,
        parse_int=lambda digits: str(int(digits)),
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_object,
    )


def load_yaml(text: str) -> Any:
    # compose (not load) keeps each scalar's text; yaml.compose raises on more
    # than one document.
    root = yaml.compose(text, Loader=_Loader)
    if root is None:
        return None
    return _yaml_value(root, _Expansion())


def _reject_constant(name: str) -> Any:
    raise SchemaSyntaxError(f"`{name}` is not valid JSON")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SchemaSyntaxError(f"duplicate key `{key}`")
        result[key] = value
    return result


def _yaml_value(node: Node, expansion: _Expansion) -> Any:
    # yaml.compose resolves aliases to the anchored node itself, so a node met
    # again while it is still being built is a recursive alias, and one met
    # again after it was built is an alias to copy.
    if id(node) in expansion.building:
        raise SchemaSyntaxError("recursive alias")
    if id(node) in expansion.built:
        value, size = expansion.built[id(node)]
        expansion.add(size)
        return copy.deepcopy(value)
    start = expansion.count
    expansion.add(1)
    expansion.building.add(id(node))
    try:
        if isinstance(node, ScalarNode):
            value = _yaml_scalar(node)
        elif isinstance(node, SequenceNode):
            _check_tag(node.tag, {SEQUENCE_TAG})
            value = [_yaml_value(child, expansion) for child in node.value]
        elif isinstance(node, MappingNode):
            value = _yaml_mapping(node, expansion)
        else:
            raise SchemaSyntaxError(f"unsupported YAML node `{type(node).__name__}`")
    finally:
        expansion.building.discard(id(node))
    expansion.built[id(node)] = (value, expansion.count - start)
    return value


def _yaml_scalar(node: ScalarNode) -> Any:
    _check_tag(node.tag, SCALAR_TAGS)
    if node.style is not None or node.tag == STR_TAG:
        return node.value
    if node.value in TRUE_WORDS:
        return True
    if node.value in FALSE_WORDS:
        return False
    if node.value in NULL_WORDS:
        return None
    return node.value


def _yaml_mapping(node: MappingNode, expansion: _Expansion) -> dict[Any, Any]:
    """Keys from `<<` merges come first, earlier sources winning; the mapping's
    own keys then override them. A key written twice is an error."""
    _check_tag(node.tag, {MAPPING_TAG})
    merged: dict[Any, Any] = {}
    own: dict[Any, Any] = {}
    seen_merge = False
    for key_node, value_node in node.value:
        key = _yaml_value(key_node, expansion)
        if isinstance(key, (dict, list)):
            raise SchemaSyntaxError("mapping keys must be scalars")

        if _merge_key(key_node):
            if seen_merge:
                raise SchemaSyntaxError("duplicate key `<<`")
            seen_merge = True
            for source in _merge_sources(_yaml_value(value_node, expansion)):
                for merged_key, merged_value in source.items():
                    if merged_key not in merged:
                        merged[merged_key] = merged_value
            continue

        if key in own:
            raise SchemaSyntaxError(f"duplicate key `{normalize_scalar(key)}`")
        own[key] = _yaml_value(value_node, expansion)

    result = dict(merged)
    result.update(own)
    return result


def _merge_key(key_node: Node) -> bool:
    return (
        isinstance(key_node, ScalarNode)
        and key_node.style is None
        and key_node.value == "<<"
        and key_node.tag == MERGE_TAG
    )


def _merge_sources(value: Any) -> list[dict[Any, Any]]:
    sources = value if isinstance(value, list) else [value]
    if not all(isinstance(source, dict) for source in sources):
        raise SchemaSyntaxError("merge key `<<` needs a mapping or a list of mappings")
    return sources


def _check_tag(tag: str, allowed: set[str] | frozenset[str]) -> None:
    if tag not in allowed:
        raise SchemaSyntaxError(f"unsupported YAML tag `{tag}`")
