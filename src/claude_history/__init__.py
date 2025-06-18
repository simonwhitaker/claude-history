import json
import re
import sys
from datetime import datetime
from pathlib import Path

import click
from simple_term_menu import TerminalMenu

BASH_INPUT_RE = r"^<bash-input>(.*)</bash-input>$"


def _is_message(data: dict) -> bool:
    """Check if the data is a message from the user."""
    return (
        data.get("message", {}).get("role") == "user"
        and not data.get("isSidechain", False)
        and not data.get("isMeta", False)
        and not data.get("toolUseResult")
        and isinstance(data.get("message", {}).get("content"), str)
    )


def _get_session_details(session_file: Path) -> tuple[datetime, str]:
    """Extract the session creation time and first prompt from the session file."""
    creation_time = datetime.fromtimestamp(session_file.stat().st_mtime)
    first_prompt = "Unknown"
    with session_file.open("r") as f:
        for line in f:
            data = json.loads(line)
            if _is_message(data):
                # Replace newlines and any following whitespace (including any further newlines) with a single, literal
                # "\n"
                first_prompt = re.sub(
                    r"\n\s*",
                    "\\\\n",
                    data["message"]["content"].strip(),
                )
                break
    return creation_time, first_prompt


def _choose_session(session_files) -> Path:
    """Prompt the user to choose a session using arrow key navigation."""

    # Build menu entries with session details
    menu_entries = []
    for session_file in session_files:
        creation_time, session_name = _get_session_details(session_file)
        entry = f"({creation_time.strftime('%Y-%m-%d %H:%M:%S')}) {session_name}"
        menu_entries.append(entry)

    # Create and show menu
    terminal_menu = TerminalMenu(
        menu_entries,
        title="Select a session (↑/↓ to navigate, Enter to select, q to quit):",
    )
    choice = terminal_menu.show()

    if choice is None:  # User pressed 'q' or Ctrl+C
        sys.exit(0)

    return session_files[choice]


@click.command()
@click.option(
    "-b",
    "--include-bash-output",
    is_flag=True,
    help="Include bash output in the history.",
)
@click.option(
    "-s", "--choose-session", is_flag=True, help="Choose a specific session to display."
)
def main(include_bash_output: bool = False, choose_session: bool = False):
    cwd = Path.cwd()
    claude_project_id = str(cwd).replace("/", "-")
    claude_project_dir = Path.home() / ".claude" / "projects" / claude_project_id

    if not claude_project_dir.exists():
        sys.stderr.write("No Claude history found for this folder\n")
        sys.exit(1)

    # Get the JSONL files in the Claude project directory, sorted by creation time
    session_files = sorted(
        claude_project_dir.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:10]
    if not session_files:
        sys.stderr.write("No session files found in the Claude project directory.\n")
        sys.exit(1)

    if choose_session:
        session_file = _choose_session(session_files)
    else:
        # Use the latest session file if not choosing
        session_file = session_files[0]

    with session_file.open("r") as f:
        for line in f:
            data = json.loads(line)
            if not _is_message(data):
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
