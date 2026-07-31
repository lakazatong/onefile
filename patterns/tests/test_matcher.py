import pytest
from onefile_patterns import PatternMatcher, normalize_pattern


def make_patterns(*patterns):
    return [normalize_pattern(p) for p in patterns]


def check(mode, patterns, cases):
    matcher = PatternMatcher(make_patterns(*patterns), mode)

    for path, expected in cases.items():
        result = matcher.matches(tuple(path.split("/")))

        assert result == expected, f"""
        mode: {mode}
        patterns: {patterns}
        path: {path}
        match: {result}
        expected: {expected}
        """.strip()


def test_normalization_basic():
    assert normalize_pattern("src") == (False, ("src",))
    assert normalize_pattern("./src/") == (False, ("src",))
    assert normalize_pattern("/src") == (False, ("src",))
    assert normalize_pattern("!./src/") == (True, ("src",))

    with pytest.raises(ValueError):
        normalize_pattern("./!src")


def test_dot_and_slash_as_starstar():
    # All forms of "current directory" become **
    for pattern in (".", "./", ".///", "////", "/./", ".//./"):
        assert normalize_pattern(pattern) == (False, ("**",))

    # With negation
    for pattern in ("!.", "!./", "!.///"):
        assert normalize_pattern(pattern) == (True, ("**",))


def test_double_dot_rejected():
    for pattern in ("../src", "src/../file", "!../../", ".."):
        with pytest.raises(ValueError, match="cannot contain '..'"):
            normalize_pattern(pattern)


def test_triple_dot_is_literal():
    assert normalize_pattern("...") == (False, ("...",))
    assert normalize_pattern("src/.../file") == (False, ("src", "...", "file"))


def test_manual_basic():
    check(
        "manual",
        ["src"],
        {
            "src/main.zig": True,
            "src/core/api.zig": True,
            "other/file.zig": False,
        },
    )


def test_manual_negation():
    check(
        "manual",
        ["src", "!src/private"],
        {
            "src/main.zig": True,
            "src/private/a.zig": False,
            "src/private/deep/a.zig": False,
        },
    )


def test_black_basic():
    check(
        "black",
        ["build"],
        {
            "src/main.zig": True,
            "build/a.o": False,
        },
    )


def test_black_negation():
    check(
        "black",
        ["build", "!build/cache"],
        {
            "build/a.o": False,
            "build/cache/a.o": True,
        },
    )


def test_manual_multiple_negations():
    check(
        "manual",
        ["src", "!src/generated", "!src/generated/private"],
        {
            "src/a.zig": True,
            "src/generated/a.zig": False,
            "src/generated/private/a.zig": False,
        },
    )


def test_absolute_windows_path_normalization():
    assert normalize_pattern(r"C:\Users\Bob\project\src") == (
        False,
        ("C:", "Users", "Bob", "project", "src"),
    )


def test_absolute_windows_path_normalization_negation():
    assert normalize_pattern(r"!C:\Users\Bob\project\src") == (
        True,
        ("C:", "Users", "Bob", "project", "src"),
    )


def test_double_star():
    check(
        "manual",
        ["my_folder/**/my_file"],
        {
            "my_folder/my_file": True,
            "my_folder/a/my_file": True,
            "my_folder/a/b/c/my_file": True,
            "my_folder/a/b/c/other": False,
            "other/my_folder/a/my_file": False,
            "my_folder/my_file/other": False,
            "my_folder/my_file/a/other": False,
        },
    )


def test_double_star_zig():
    check(
        "manual",
        ["src/**/*.zig"],
        {
            "src/main.zig": True,
            "src/a/main.zig": True,
            "src/a/b/main.zig": True,
            "src/a/b/main.js": False,
            "src/.zig": True,
        },
    )


def test_double_star_root_zig():
    check(
        "manual",
        ["**/*.zig"],
        {
            ".zig": True,
            "root.zig": True,
            "src/main.zig": True,
            "src/a/main.zig": True,
            "src/a/b/main.zig": True,
            "src/a/b/main.js": False,
            "src/.zig": True,
        },
    )
