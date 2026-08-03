import argparse
import sys
from pathlib import Path

from onefile_patterns import PatternMatcher, load_patterns, normalize_pattern

root_dir = Path()

def is_text_file(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)

        if b"\x00" in chunk:
            return False

        chunk.decode("utf-8")
        return True

    except (UnicodeDecodeError, OSError):
        return False

def iter_project_files(root_dir, base_patterns, always_exclude):
    root_dir = Path(root_dir).resolve()
    active_patterns = list(base_patterns)  # copy; will be mutated

    def walk(current_dir, current_parts):
        added = []

        # Load patterns from this directory if files exist
        inc_file = current_dir / "onefile_include.txt"
        exc_file = current_dir / "onefile_exclude.txt"

        if inc_file.exists():
            for neg, parts in load_patterns(str(inc_file)):
                new_parts = current_parts + parts
                added.append((neg, new_parts))

        if exc_file.exists():
            for neg, parts in load_patterns(str(exc_file)):
                # Negation toggled: include → exclude, exclude → include
                new_parts = current_parts + parts
                added.append((not neg, new_parts))

        if added:
            active_patterns.extend(added)

        # Build matcher from the current stack
        matcher = PatternMatcher(active_patterns)

        # Process files in current_dir
        try:
            entries = sorted(current_dir.iterdir(), key=lambda e: e.name)
        except (PermissionError, OSError):
            return

        for entry in entries:
            try:
                if entry.is_file():
                    if entry.name in always_exclude:
                        continue
                    if not is_text_file(entry):
                        continue
                    rel = entry.relative_to(root_dir)
                    parts = rel.parts
                    if matcher.matches(parts):
                        yield entry

                elif entry.is_dir():
                    sub_parts = current_parts + (entry.name,)
                    # Only descend if there's any chance of a match below
                    if matcher.can_have_matches_below(sub_parts):
                        yield from walk(entry, sub_parts)

            except OSError:
                continue

        # Pop the patterns we added for this directory
        if added:
            del active_patterns[-len(added) :]

    yield from walk(root_dir, ())


def preview_files(root_dir, base_patterns, always_exclude):
    for path in iter_project_files(root_dir, base_patterns, always_exclude):
        print(path.relative_to(root_dir))


def write_output(root_dir, output_file, base_patterns, always_exclude):
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Generated using: {' '.join(sys.argv)}\nUnder {root_dir}\n\n")
        for path in iter_project_files(root_dir, base_patterns, always_exclude):
            rel = path.relative_to(root_dir)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError) as e:
                print(e)
                continue
            out.write(f"{rel}\n\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")
            out.write("\n")


def main():
    global root_dir
    parser = argparse.ArgumentParser(
        description=(
            "Bundle project files into one text file.\n\n"
            "Patterns can be provided directly on the command line (positional arguments).\n"
            "Additionally, if a directory contains a 'onefile_include.txt' or "
            "'onefile_exclude.txt' file, its patterns are automatically loaded "
            "for that directory and its descendants.\n\n"
            "Pattern matching:\n"
            "  - Patterns are literal path components (with glob support).\n"
            "  - A pattern matches itself and everything below it.\n"
            "  - Leading '!' negates a pattern.\n\n"
            "Default file semantics:\n"
            "  - onefile_include.txt : patterns are added as‑is.\n"
            "  - onefile_exclude.txt : all patterns in the file are negated (toggle).\n"
            "  - These files are loaded from every directory as the walk progresses.\n"
            "  - Patterns are relative to their directory.\n\n"
            "Examples:\n"
            "  onefile src/core README.md                 # include two specific paths\n"
            "  onefile .                                  # include everything ('.' -> '**')\n"
            "  onefile --dry                              # list files without writing\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "patterns",
        nargs="*",
        help="Include path patterns (manual mode)",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default=".",
        help="Root directory to start walking (default: .)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="onefile_out.txt",
        help="Output file (default: onefile_out.txt)",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Dry-run (list matching files only)",
    )

    args = parser.parse_args()

    root_dir = Path(args.directory).resolve()
    output_file = Path(args.output).resolve()

    # Base patterns come ONLY from command line
    base_patterns = [normalize_pattern(p) for p in args.patterns]

    # Always exclude the script itself and the output file
    script_name = Path(__file__).name
    always_exclude = {script_name, output_file.name}

    if args.dry:
        preview_files(root_dir, base_patterns, always_exclude)
    else:
        write_output(root_dir, output_file, base_patterns, always_exclude)


if __name__ == "__main__":
    main()
