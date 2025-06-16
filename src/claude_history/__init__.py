import json
import re
from pathlib import Path

import click

BASH_INPUT_RE = r"^<bash-input>(.*)</bash-input>$"


@click.command()
@click.option(
    "-b",
    "--include-bash-output",
    is_flag=True,
    help="Include bash output in the history.",
)
def main(include_bash_output: bool = False):
    cwd = Path.cwd()
    claude_project_id = str(cwd).replace("/", "-")
    claude_project_dir = Path.home() / ".claude" / "projects" / claude_project_id

    # Get the latest jsonl file in the Claude project directory
    latest_mtime = 0
    latest_session_file = None
    for f in claude_project_dir.iterdir():
        if f.is_file() and f.suffix == ".jsonl" and f.stat().st_mtime > latest_mtime:
            latest_mtime = f.stat().st_mtime
            latest_session_file = f

    if latest_session_file is None:
        # If no files found, look for session files in subdirectories
        print("No files found in the Claude project directory.")
        return

    with latest_session_file.open("r") as f:
        for line in f:
            data = json.loads(line)
            if data.get("message", {}).get("role") != "user":
                continue
            if data.get("isSidechain", False):
                continue
            if data.get("isMeta", False):
                continue
            if data.get("toolUseResult"):
                continue
            if type(data.get("message", {}).get("content")) is not str:
                continue

            content = data["message"]["content"].strip()

            if content.startswith("<bash-stdout>") and not include_bash_output:
                continue

            # Reformat bash input, removing XML tags and starting with ! instead.
            if match := re.match(BASH_INPUT_RE, content):
                content = f"! {match.group(1).strip()}"

            print(f"- {content}")


if __name__ == "__main__":
    main()
