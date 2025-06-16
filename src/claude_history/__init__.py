import json
from pathlib import Path

import click


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

    # Get the top-level contents of claude_project_dir in order of when they were last modified
    sorted_files = sorted(
        claude_project_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True
    )
    if len(sorted_files) == 0:
        print("No files found in the Claude project directory.")

    latest_session_file = sorted_files[0]
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

            message = data["message"]["content"].strip()
            if message.startswith("<bash-stdout>") and not include_bash_output:
                continue

            print(f"- {message}")


if __name__ == "__main__":
    main()
