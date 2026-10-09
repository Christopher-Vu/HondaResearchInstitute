"""Practice-gap predicates (gaps/practice/practice_v1.yaml) evaluated against one route's metadata.

A predicate is a list of conditions that must all hold. A condition is {field, op, value}, where
field is a dotted path into the metadata (`scenario`, `param.blocker_model`,
`weather.sun_altitude_angle`) and op is one of ==, in, <, <=, >, >=. A field the metadata does not
have makes its condition false. Ordering comparisons read both sides as numbers, so the string "40"
from an XML attribute compares like the number 40, and a side that is not a number makes the
condition false.
"""
from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any

MISSING = object()


def as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def same(actual: Any, expected: Any) -> bool:
    actual_number, expected_number = as_number(actual), as_number(expected)
    if actual_number is not None and expected_number is not None:
        return actual_number == expected_number
    return bool(actual == expected)


def ordered(compare: Callable[[float, float], bool]) -> Callable[[Any, Any], bool]:
    def apply(actual: Any, expected: Any) -> bool:
        actual_number, expected_number = as_number(actual), as_number(expected)
        return actual_number is not None and expected_number is not None and compare(actual_number, expected_number)
    return apply


OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "==": same,
    "in": lambda actual, options: any(same(actual, option) for option in options),
    "<": ordered(operator.lt),
    "<=": ordered(operator.le),
    ">": ordered(operator.gt),
    ">=": ordered(operator.ge),
}


def lookup(metadata: dict[str, Any], dotted_path: str) -> Any:
    value: Any = metadata
    for key in dotted_path.split("."):
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def holds(condition: dict[str, Any], metadata: dict[str, Any]) -> bool:
    if condition["op"] not in OPERATORS:
        raise ValueError(f"Unknown predicate operator {condition['op']!r}; use one of {', '.join(OPERATORS)}")
    actual = lookup(metadata, condition["field"])
    return actual is not MISSING and OPERATORS[condition["op"]](actual, condition["value"])


def matches(predicate: list[dict[str, Any]], metadata: dict[str, Any]) -> bool:
    if not predicate:
        raise ValueError("A predicate needs at least one condition; an empty one would match every route")
    return all([holds(condition, metadata) for condition in predicate])
