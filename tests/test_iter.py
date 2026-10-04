from onefile_patterns import normalize_pattern

from onefile.__main__ import iter_project_files


def make_pattern(priority, pattern):
    return (priority, *normalize_pattern(pattern))


def test_cli_generic_include_does_not_override_specific_file_exclude(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()

    (venv / "foo.py").write_text("print('hello')")
    (tmp_path / "foo.py").write_text("print('hello')")

    patterns = [
        make_pattern(1, "**/*.py"),
        make_pattern(0, "!.venv"),
    ]

    files = list(iter_project_files(tmp_path, patterns, set()))

    assert venv / "foo.py" not in files
    assert tmp_path / "foo.py" in files


def test_cli_specific_include_overrides_file_exclude(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()

    target = venv / "foo.py"
    target.write_text("print('hello')")

    (tmp_path / "onefile_exclude.txt").write_text(".venv\n")

    patterns = [make_pattern(1, ".venv/foo.py")]

    files = list(iter_project_files(tmp_path, patterns, set()))

    assert target in files


def test_same_specificity(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    target = src / "__init__.py"
    target.write_text("print('hello')")

    (tmp_path / "onefile_exclude.txt").write_text("**/__init__.py\n")

    patterns = [make_pattern(1, "src/**")]

    files = list(iter_project_files(tmp_path, patterns, set()))

    assert not target in files


def test_tricky_specificity(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    my_package_egg_info = src / "my-package.egg-info"
    my_package_egg_info.mkdir()

    target = my_package_egg_info / "PKG-INFO"
    target.write_text("Metadata-Version: 2.4")

    (tmp_path / "onefile_exclude.txt").write_text("**/*.egg-info\n")

    patterns = [make_pattern(1, "src/**")]

    files = list(iter_project_files(tmp_path, patterns, set()))

    assert not target in files
