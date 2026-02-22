from __future__ import annotations

import argparse
import pathlib
import tomllib


def export_requirements(pyproject_path: pathlib.Path, output_path: pathlib.Path) -> None:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})

    deps = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    dev_deps = optional.get("dev", [])
    deps.extend(dev_deps)

    seen: set[str] = set()
    ordered: list[str] = []
    for item in deps:
        if not isinstance(item, str):
            continue
        spec = item.strip()
        if spec == "" or spec in seen:
            continue
        seen.add(spec)
        ordered.append(spec)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(ordered) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export dependency list from pyproject.toml to requirements.txt"
    )
    parser.add_argument("pyproject", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    export_requirements(args.pyproject, args.output)


if __name__ == "__main__":
    main()
