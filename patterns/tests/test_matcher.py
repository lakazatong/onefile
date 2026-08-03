import itertools

import pytest

from onefile_patterns import PatternMatcher, normalize_pattern


def make_patterns(*patterns):
    return [normalize_pattern(p) for p in patterns]


def check(patterns, cases, permutations=True):
    orders = (
        itertools.permutations(patterns)
        if permutations
        else [patterns]
    )

    for order in orders:
        matcher = PatternMatcher(make_patterns(*order))

        for path, expected in cases.items():
            result = matcher.matches(tuple(path.split("/")))

            assert result == expected, f"""
            patterns: {order}
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
    for pattern in (".", "./", ".///", "////", "/./", ".//./"):
        assert normalize_pattern(pattern) == (False, ("**",))

    for pattern in ("!.", "!./", "!.///"):
        assert normalize_pattern(pattern) == (True, ("**",))


def test_double_dot_rejected():
    for pattern in ("../src", "src/../file", "!../../", ".."):
        with pytest.raises(ValueError, match="cannot contain '..'"):
            normalize_pattern(pattern)


def test_triple_dot_is_literal():
    assert normalize_pattern("...") == (False, ("...",))
    assert normalize_pattern("src/.../file") == (
        False,
        ("src", "...", "file"),
    )


def test_include_basic():
    check(
        ["src"],
        {
            "src/main.zig": True,
            "src/core/api.zig": True,
            "other/file.zig": False,
        },
    )


def test_exclude_basic():
    check(
        ["src", "!src/private"],
        {
            "src/main.zig": True,
            "src/private/a.zig": False,
            "src/private/deep/a.zig": False,
        },
    )


def test_exclude_directory():
    check(
        ["!build"],
        {
            "src/main.zig": True,
            "build/a.o": False,
        },
    )


def test_reinclude_directory():
    check(
        ["!build", "build/cache"],
        {
            "build/a.o": False,
            "build/cache/a.o": True,
        },
    )


def test_nested_exclusions():
    check(
        ["src", "!src/generated", "!src/generated/private"],
        {
            "src/a.zig": True,
            "src/generated/a.zig": False,
            "src/generated/private/a.zig": False,
        },
    )


def test_specificity():
    check(
        ["!*.txt", "credits.txt"],
        {
            "credits.txt": True,
            "a.txt": False,
            "dir/a.txt": False,
            "image.png": False,
        },
    )

    check(
        ["*.txt", "!credits.txt"],
        {
            "credits.txt": False,
            "a.txt": True,
            "dir/a.txt": False,
            "image.png": False,
        },
    )

    check(
        ["src", "!src/private", "src/private/public"],
        {
            "src/a": True,
            "src/private/a": False,
            "src/private/public/a": True,
        },
    )

    check(
        ["!src", "src/private", "!src/private/public"],
        {
            "src/a": False,
            "src/private/a": True,
            "src/private/public/a": False,
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


def test_equal_specificity_last_one_wins():
    check(
        ["*.txt", "!*.txt"],
        {
            "a.txt": False,
        },
        permutations=False,
    )


def test_double_star_is_less_specific():
    check(
        ["**/*.zig", "!src/main.zig"],
        {
            "src/main.zig": False,
            "other/main.zig": True,
        },
    )


def test_no_patterns():
    check(
        [],
        {
            "anything": True,
            "a/b/c": True,
        },
    )


def test_root_include_and_exclude():
    check(
        ["."],
        {
            "file.txt": True,
            "dir/file.txt": True,
        },
    )

    check(
        ["!."],
        {
            "file.txt": False,
            "dir/file.txt": False,
        },
    )


def test_directory_pattern_matches_contents():
    check(
        ["src/file"],
        {
            "src/file": True,
            "src/file/a": True,
            "src": False,
            "src_other/file": False,
        },
    )


def test_special_component_names():
    check(
        ["*.txt"],
        {
            ".txt": True,
            "file.txt": True,
            "file.txt.bak": False,
            "txt": False,
        },
    )


def test_wildcard_component():
    check(
        ["a_*_b_*_c.txt"],
        {
            "a_x_b_y_c.txt": True,
            "a_test_b_world_c.txt": True,
            "a_hello_world_b_123_c.txt": True,
            "a__b__c.txt": True,
            "a_x_b_c.txt": False,
            "a_x_y.txt": False,
            "x_a_x_b_y_c.txt": False,
            "a_x_b_y_c.txt.bak": False,
            "a_b_b_c.txt": False,
            "a_b_b_b_b_c.txt": True,
        },
    )
