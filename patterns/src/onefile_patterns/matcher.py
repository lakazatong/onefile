import re
from pathlib import Path

# patterns


def normalize_pattern(value):
    original = value
    value = value.replace("\\", "/")

    # ---- negation handling ----
    if "!" in value:
        if not value.startswith("!"):
            raise ValueError(f"Invalid pattern: {value}")
        if value.count("!") != 1:
            raise ValueError(f"Invalid pattern: {value}")
    negated = value.startswith("!")
    if negated:
        value = value[1:]

    # ---- strip leading cruft ----
    value = value.lstrip("/")
    value = value.removeprefix("./")

    # ---- collapse repeated slashes ----
    while "//" in value:
        value = value.replace("//", "/")

    value = value.rstrip("/")

    # ---- split into components ----
    parts = [part for part in value.split("/") if part]

    # ---- reject attempts to go above root ----
    if ".." in parts:
        raise ValueError(f"Pattern cannot contain '..' (would escape root): {original}")

    # ---- special: "everything under root" ----
    if not parts or parts == ["."]:
        parts = ["**"]

    return negated, tuple(parts)


def load_patterns(filter_file):
    if not Path(filter_file).exists():
        return []

    with open(filter_file, "r", encoding="utf-8") as f:
        return [
            normalize_pattern(line.strip())
            for line in f
            if line.strip() and not line.startswith("#")
        ]


# pattern matcher


def match_component(pattern, value):
    if "*" not in pattern:
        return pattern == value

    regex = "^" + re.escape(pattern).replace("\\*", ".*") + "$"

    return re.match(regex, value) is not None


def match_path(pattern, path):
    if "**" in pattern:

        def match(pattern_index, path_index):
            if pattern_index == len(pattern):
                return path_index == len(path)

            if pattern[pattern_index] == "**":
                return match(pattern_index + 1, path_index) or (
                    path_index < len(path) and match(pattern_index, path_index + 1)
                )

            if path_index >= len(path):
                return False

            if not match_component(pattern[pattern_index], path[path_index]):
                return False

            return match(pattern_index + 1, path_index + 1)

        return match(0, 0)

    if len(pattern) > len(path):
        return False

    return all(
        match_component(pattern_part, path_part)
        for pattern_part, path_part in zip(pattern, path)
    )


def can_match_below(pattern, path):
    def recurse(pattern_index, path_index):
        if path_index == len(path):
            return True

        if pattern_index == len(pattern):
            return False

        if pattern[pattern_index] == "**":
            return recurse(pattern_index + 1, path_index) or recurse(
                pattern_index, path_index + 1
            )

        if not match_component(pattern[pattern_index], path[path_index]):
            return False

        return recurse(pattern_index + 1, path_index + 1)

    return recurse(0, 0)


def pattern_specificity(pattern):
    return (
        sum(part != "**" for part in pattern),
        -sum(part == "**" for part in pattern),
        -sum("*" in part for part in pattern),
    )


class PatternMatcher:
    def __init__(self, patterns):
        self.patterns = patterns

    def matches(self, path_parts):
        matched = []

        has_include = any(not negated for negated, _ in self.patterns)

        for index, (negated, pattern) in enumerate(self.patterns):
            if match_path(pattern, path_parts):
                matched.append(
                    (pattern_specificity(pattern), index, negated)
                )

        if not matched:
            return not has_include

        _, _, negated = max(matched, key=lambda x: (x[0], x[1]))

        return not negated

    def can_have_matches_below(self, path_parts):
        for _, pattern in self.patterns:
            if can_match_below(pattern, path_parts):
                return True

        return False