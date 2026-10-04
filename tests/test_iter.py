from onefile_patterns import normalize_pattern

from onefile.__main__ import iter_project_files


def make_pattern(priority, pattern):
    return (priority, *normalize_pattern(pattern))


def make_tree(root, paths):
    for path in paths:
        path = root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")


def check(tmp_path, paths, patterns, expected, filter_files=None):
    make_tree(tmp_path, paths)

    for name, content in (filter_files or {}).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    matcher = [make_pattern(1, pattern) for pattern in patterns]

    always_exclude = {"onefile_include.txt", "onefile_exclude.txt"}

    result = {
        path.relative_to(tmp_path).as_posix()
        for path in iter_project_files(
            tmp_path,
            matcher,
            always_exclude,
        )
    }

    assert result == set(expected)


def test_cli_generic_include_does_not_override_specific_file_exclude(tmp_path):
    check(
        tmp_path,
        paths=[
            ".venv/foo.py",
            "foo.py",
        ],
        patterns=[
            "**/*.py",
            "!.venv",
        ],
        expected=["foo.py"],
    )


def test_cli_specific_include_overrides_file_exclude(tmp_path):
    check(
        tmp_path,
        paths=[".venv/foo.py"],
        patterns=[".venv/foo.py"],
        filter_files={"onefile_exclude.txt": ".venv\n"},
        expected=[".venv/foo.py"],
    )


def test_specific_file_exclude_overrides_generic_include(tmp_path):
    check(
        tmp_path,
        paths=["src/__init__.py"],
        patterns=["src/**"],
        filter_files={"onefile_exclude.txt": "**/__init__.py\n"},
        expected=[],
    )


def test_egg_info_excluded_from_src_glob(tmp_path):
    check(
        tmp_path,
        paths=[
            "src/mypackage/dead/beef.py",
            "src/mypackage/foo.py",
            "src/mypackage.egg-info/PKG-INFO",
        ],
        patterns=["src/**"],
        filter_files={"onefile_exclude.txt": "**/*.egg-info\n"},
        expected=[
            "src/mypackage/dead/beef.py",
            "src/mypackage/foo.py",
        ],
    )


def test_cli_wins_same_specificity(tmp_path):
    check(
        tmp_path,
        paths=["src/foo.py"],
        patterns=["src/foo.py"],
        filter_files={"onefile_exclude.txt": "src/foo.py\n"},
        expected=["src/foo.py"],
    )
