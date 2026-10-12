"""PostToolUse hook: Claude が編集した .py ファイルを ruff で整形・自動修正する。

直せない lint エラーが残った場合は stderr に出して exit 2 で終了し、Claude に修正を促す。
"""

import json
import os
import subprocess
import sys

payload = json.load(sys.stdin)
file_path = payload.get("tool_input", {}).get("file_path", "")
if not file_path.endswith(".py") or not os.path.exists(file_path):
    sys.exit(0)

project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())


def ruff(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--quiet", "ruff", *args, file_path],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )


ruff("format")
result = ruff("check", "--fix", "--quiet")
if result.returncode != 0:
    print(f"ruff check で未解決の指摘があります:\n{result.stdout}{result.stderr}", file=sys.stderr)
    sys.exit(2)
