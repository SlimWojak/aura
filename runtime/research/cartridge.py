"""Load and validate paper-only Aura research cartridges.

The repository intentionally avoids a YAML dependency. The parser below supports
only the boring subset used by ``research/cartridges/*.yaml``: mappings, scalar
values, empty ``{}``/``[]`` literals, and scalar lists.
"""

from __future__ import annotations

from pathlib import Path
import ast
import re
from typing import Any, Mapping, Sequence


STATUS_VALUES = {"draft", "queued", "tested", "killed", "kept"}
ENTRY_MODES = {"always_on", "tk_cross", "cloud_bias", "tk_cloud_bias"}
SIDES = {"long", "short"}
CLOUD_RULES = {"above_for_long_below_for_short", "outside_cloud", "none"}
TK_RULES = {"tenkan_over_kijun_for_long_under_for_short", "tk_cross_only", "none"}
CHIKOU_MODES = {"close", "strict"}
EXIT_MODES = {"bias_flip", "flat_on_rule_fail", "opposite_signal", "time_stop"}
REGIME_TYPES = {"adx", "er", "cloud_thickness", "none"}
BASELINE_METRICS = {"total_pnl_points", "max_drawdown_points", "win_rate", "profit_factor"}

TOP_LEVEL_FIELDS = {
    "id",
    "title",
    "status",
    "thesis",
    "symbol",
    "tf",
    "baseline_ref",
    "ichimoku",
    "entry_rules",
    "exit_rules",
    "regime",
    "kill_criteria",
    "sources",
    "notes",
}
REQUIRED_FIELDS = TOP_LEVEL_FIELDS - {"notes"}
ICHIMOKU_FIELDS = {"tenkan", "kijun", "senkou_b", "displacement"}
ENTRY_FIELDS = {
    "mode",
    "allowed_sides",
    "require_close_vs_cloud",
    "require_tk_state",
    "require_chikou_confirmation",
    "chikou_mode",
}
EXIT_FIELDS = {"mode", "close_on_flat", "close_on_opposite", "max_bars_in_trade"}
REGIME_FIELDS = {"type", "params"}
KILL_FIELDS = {
    "max_dd_points",
    "min_trades",
    "must_beat_baseline",
    "baseline_metric",
    "notes",
}

ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)$")


def load_cartridge(path: str | Path) -> dict[str, Any]:
    """Read a cartridge YAML file and validate the Aura cartridge contract."""

    cartridge_path = Path(path)
    raw = _parse_yaml_subset(cartridge_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{cartridge_path}: cartridge root must be a mapping")
    return validate_cartridge(raw, source=cartridge_path)


def load_cartridges(root: str | Path) -> list[dict[str, Any]]:
    """Load all ``*.yaml`` cartridges from a directory in stable path order."""

    root_path = Path(root)
    return [load_cartridge(path) for path in sorted(root_path.glob("*.yaml"))]


def validate_cartridge(
    cartridge: Mapping[str, Any],
    *,
    source: str | Path | None = None,
) -> dict[str, Any]:
    """Return a normalized dict when required fields and enums are valid."""

    label = str(source) if source is not None else "cartridge"
    _require_fields(cartridge, REQUIRED_FIELDS, label)
    _reject_unknown_fields(cartridge, TOP_LEVEL_FIELDS, label)

    _require_string(cartridge, "id", label)
    if ID_RE.fullmatch(str(cartridge["id"])) is None:
        raise ValueError(f"{label}: id must be snake_case")
    for field in ("title", "thesis", "symbol", "tf", "baseline_ref"):
        _require_string(cartridge, field, label)
    _require_enum(cartridge, "status", STATUS_VALUES, label)

    ichimoku = _require_mapping(cartridge, "ichimoku", label)
    _require_fields(ichimoku, ICHIMOKU_FIELDS, f"{label}: ichimoku")
    _reject_unknown_fields(ichimoku, ICHIMOKU_FIELDS, f"{label}: ichimoku")
    for field in ICHIMOKU_FIELDS:
        _require_positive_int(ichimoku, field, f"{label}: ichimoku")

    entry_rules = _require_mapping(cartridge, "entry_rules", label)
    _require_fields(entry_rules, ENTRY_FIELDS, f"{label}: entry_rules")
    _reject_unknown_fields(entry_rules, ENTRY_FIELDS, f"{label}: entry_rules")
    _require_enum(entry_rules, "mode", ENTRY_MODES, f"{label}: entry_rules")
    _require_enum(
        entry_rules,
        "require_close_vs_cloud",
        CLOUD_RULES,
        f"{label}: entry_rules",
    )
    _require_enum(entry_rules, "require_tk_state", TK_RULES, f"{label}: entry_rules")
    _require_bool(entry_rules, "require_chikou_confirmation", f"{label}: entry_rules")
    _require_enum(entry_rules, "chikou_mode", CHIKOU_MODES, f"{label}: entry_rules")
    allowed_sides = _require_list(entry_rules, "allowed_sides", f"{label}: entry_rules")
    if not allowed_sides:
        raise ValueError(f"{label}: entry_rules.allowed_sides must not be empty")
    for side in allowed_sides:
        if side not in SIDES:
            raise ValueError(f"{label}: unsupported entry side {side!r}")

    exit_rules = _require_mapping(cartridge, "exit_rules", label)
    _require_fields(exit_rules, EXIT_FIELDS, f"{label}: exit_rules")
    _reject_unknown_fields(exit_rules, EXIT_FIELDS, f"{label}: exit_rules")
    _require_enum(exit_rules, "mode", EXIT_MODES, f"{label}: exit_rules")
    _require_bool(exit_rules, "close_on_flat", f"{label}: exit_rules")
    _require_bool(exit_rules, "close_on_opposite", f"{label}: exit_rules")
    max_bars = exit_rules["max_bars_in_trade"]
    if max_bars is not None:
        _require_positive_int(exit_rules, "max_bars_in_trade", f"{label}: exit_rules")

    regime = _require_mapping(cartridge, "regime", label)
    _require_fields(regime, REGIME_FIELDS, f"{label}: regime")
    _reject_unknown_fields(regime, REGIME_FIELDS, f"{label}: regime")
    _require_enum(regime, "type", REGIME_TYPES, f"{label}: regime")
    params = _require_mapping(regime, "params", f"{label}: regime")
    if regime["type"] == "none" and params:
        raise ValueError(f"{label}: regime.params must be empty when type is none")

    kill_criteria = _require_mapping(cartridge, "kill_criteria", label)
    _require_fields(kill_criteria, KILL_FIELDS, f"{label}: kill_criteria")
    _reject_unknown_fields(kill_criteria, KILL_FIELDS, f"{label}: kill_criteria")
    _require_positive_number(kill_criteria, "max_dd_points", f"{label}: kill_criteria")
    _require_positive_int(kill_criteria, "min_trades", f"{label}: kill_criteria")
    _require_bool(kill_criteria, "must_beat_baseline", f"{label}: kill_criteria")
    _require_enum(
        kill_criteria,
        "baseline_metric",
        BASELINE_METRICS,
        f"{label}: kill_criteria",
    )
    _require_string(kill_criteria, "notes", f"{label}: kill_criteria")

    sources = _require_list(cartridge, "sources", label)
    for source_value in sources:
        if not isinstance(source_value, str) or not source_value.strip():
            raise ValueError(f"{label}: sources entries must be non-empty strings")
    if "notes" in cartridge:
        _require_string(cartridge, "notes", label)

    return dict(cartridge)


def _parse_yaml_subset(text: str) -> Any:
    lines = _logical_lines(text)
    if not lines:
        return {}
    result, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        line_number = lines[index][2]
        raise ValueError(f"unexpected content at line {line_number}")
    return result


def _logical_lines(text: str) -> list[tuple[int, str, int]]:
    logical: list[tuple[int, str, int]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("\t"):
            raise ValueError(f"tabs are not supported at line {line_number}")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        logical.append((indent, raw_line.strip(), line_number))
    return logical


def _parse_block(
    lines: Sequence[tuple[int, str, int]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    current_indent, stripped, line_number = lines[index]
    if current_indent != indent:
        raise ValueError(f"unexpected indentation at line {line_number}")
    if stripped.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(
    lines: Sequence[tuple[int, str, int]],
    index: int,
    indent: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current_indent, stripped, line_number = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"unexpected nested mapping at line {line_number}")
        if stripped.startswith("- "):
            raise ValueError(f"list item where mapping key expected at line {line_number}")
        if ":" not in stripped:
            raise ValueError(f"mapping entry must contain ':' at line {line_number}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty mapping key at line {line_number}")
        raw_value = raw_value.strip()
        if raw_value:
            result[key] = _parse_scalar(raw_value, line_number)
            index += 1
            continue

        if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
            raise ValueError(f"missing nested value for {key!r} at line {line_number}")
        value, index = _parse_block(lines, index + 1, lines[index + 1][0])
        result[key] = value
    return result, index


def _parse_list(
    lines: Sequence[tuple[int, str, int]],
    index: int,
    indent: int,
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current_indent, stripped, line_number = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"unexpected nested list content at line {line_number}")
        if not stripped.startswith("- "):
            break
        raw_value = stripped[2:].strip()
        if not raw_value:
            if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
                raise ValueError(f"missing nested list value at line {line_number}")
            value, index = _parse_block(lines, index + 1, lines[index + 1][0])
            result.append(value)
            continue
        result.append(_parse_scalar(raw_value, line_number))
        index += 1
    return result, index


def _parse_scalar(raw_value: str, line_number: int) -> Any:
    if raw_value in {"{}", "[]"}:
        return {} if raw_value == "{}" else []
    lowered = raw_value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if raw_value.startswith(("'", '"')):
        try:
            value = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"invalid quoted scalar at line {line_number}") from exc
        if not isinstance(value, str):
            raise ValueError(f"quoted scalar must be a string at line {line_number}")
        return value
    if INT_RE.fullmatch(raw_value) is not None:
        return int(raw_value)
    if FLOAT_RE.fullmatch(raw_value) is not None:
        return float(raw_value)
    return raw_value


def _require_fields(values: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"{label}: missing required fields: {', '.join(missing)}")


def _reject_unknown_fields(values: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"{label}: unknown fields: {', '.join(unknown)}")


def _require_mapping(values: Mapping[str, Any], field: str, label: str) -> Mapping[str, Any]:
    value = values[field]
    if not isinstance(value, Mapping):
        raise ValueError(f"{label}: {field} must be a mapping")
    return value


def _require_list(values: Mapping[str, Any], field: str, label: str) -> list[Any]:
    value = values[field]
    if not isinstance(value, list):
        raise ValueError(f"{label}: {field} must be a list")
    return value


def _require_string(values: Mapping[str, Any], field: str, label: str) -> None:
    value = values[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: {field} must be a non-empty string")


def _require_bool(values: Mapping[str, Any], field: str, label: str) -> None:
    if not isinstance(values[field], bool):
        raise ValueError(f"{label}: {field} must be a boolean")


def _require_enum(
    values: Mapping[str, Any],
    field: str,
    allowed: set[str],
    label: str,
) -> None:
    value = values[field]
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{label}: {field} must be one of: {allowed_values}")


def _require_positive_int(values: Mapping[str, Any], field: str, label: str) -> None:
    value = values[field]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label}: {field} must be a positive integer")


def _require_positive_number(values: Mapping[str, Any], field: str, label: str) -> None:
    value = values[field]
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label}: {field} must be a positive number")
