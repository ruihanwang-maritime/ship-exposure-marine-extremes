"""
Generate notebooks/ from code/, one notebook per script.

The .py files under code/ are the source of truth. This produces an interactive
copy of each for checking intermediate results: the script is split into cells
at top-level boundaries (banner comments, def, class), the module docstring
becomes a markdown header, the `if __name__` guard is dropped, and a final cell
calls main().

Each notebook defines __file__ up front, so the scripts' own
`Path(__file__).resolve().parents[1]` path handling keeps working unchanged.

Re-run after editing any script:  python tools/make_notebooks.py
"""
import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "code"
OUT = REPO / "notebooks"

BANNER = "# ---"
GUARD = 'if __name__ == "__main__":'


def split_cells(src):
    """Break a module into chunks at top-level banners and definitions."""
    lines = src.splitlines()
    chunks, cur = [], []

    def flush():
        text = "\n".join(cur).strip("\n")
        if text.strip():
            chunks.append(text)
        cur.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(GUARD):
            break                                  # entry point re-added below
        starts_block = (line.startswith(BANNER)
                        or line.startswith("def ")
                        or line.startswith("class "))
        if starts_block and cur:
            # keep a banner comment attached to the definition beneath it
            back = len(cur)
            while back and cur[back - 1].startswith("#"):
                back -= 1
            if back < len(cur) and not line.startswith(BANNER):
                trailing = cur[back:]
                del cur[back:]
                flush()
                cur.extend(trailing)
            else:
                flush()
        cur.append(line)
        i += 1
    flush()
    return chunks


def to_notebook(path):
    src = path.read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(src)) or path.stem
    body = src.split('"""', 2)[-1].lstrip("\n") if src.startswith('"""') else src

    cells = [{"cell_type": "markdown", "metadata": {},
              "source": [f"# `{path.name}`\n", "\n", "```\n", doc.strip() + "\n", "```\n"]},
             {"cell_type": "code", "metadata": {}, "execution_count": None,
              "outputs": [],
              "source": ["# the scripts resolve their paths from __file__; define it here\n",
                         f'__file__ = r"{path}"\n']}]
    for chunk in split_cells(body):
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                      "outputs": [], "source": [l + "\n" for l in chunk.splitlines()]})
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": ["main()\n"]})

    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3",
                                      "language": "python", "name": "python3"},
                       "language_info": {"name": "python",
                                         "version": sys.version.split()[0]}}}
    dst = OUT / (path.stem + ".ipynb")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    return dst, len(cells)


def main():
    scripts = sorted(p for p in CODE.glob("*.py") if p.name != "config.py")
    for p in scripts:
        dst, n = to_notebook(p)
        print(f"    {dst.relative_to(REPO)}   ({n} cells)")
    print(f"\n    {len(scripts)} notebooks written to {OUT.relative_to(REPO)}/")
    print("    config.py is imported, not converted - edit it as a module")


if __name__ == "__main__":
    main()
