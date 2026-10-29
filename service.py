"""Start and stop the assistant through macOS's service manager (launchd).

The assistant runs as a launch agent with KeepAlive, which tells macOS to
restart it whenever it exits. That's why the old Stop button (killing the
process with `pkill -f main.py`) never worked: macOS restarted it right
away. `pkill -f main.py` also killed ANY program with "main.py" in its
command line, not just this one.

Here we ask launchd itself to start/stop the service, by its label.
"""

import os
import subprocess

ASSISTANT_LABEL = "com.clipboardcalendar.assistant"
MENU_LABEL = "com.clipboardcalendar.menu"
LAUNCH_AGENTS = os.path.expanduser("~/Library/LaunchAgents")


def _domain() -> str:
    return f"gui/{os.getuid()}"  # this user's logged-in session


def _run(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def is_running(label: str = ASSISTANT_LABEL, run=_run) -> bool:
    result = run(["print", f"{_domain()}/{label}"])
    return result.returncode == 0 and "state = running" in result.stdout


def start(label: str = ASSISTANT_LABEL, run=_run) -> None:
    """Load the service if it was stopped; macOS then starts it."""
    if run(["print", f"{_domain()}/{label}"]).returncode != 0:
        run(["bootstrap", _domain(), os.path.join(LAUNCH_AGENTS, f"{label}.plist")])
    else:
        run(["kickstart", f"{_domain()}/{label}"])


def stop(label: str = ASSISTANT_LABEL, run=_run) -> None:
    """Unload the service so KeepAlive can't restart it. It stays stopped
    until Start is clicked or you next log in."""
    run(["bootout", f"{_domain()}/{label}"])


def restart(label: str = ASSISTANT_LABEL, run=_run) -> None:
    run(["kickstart", "-k", f"{_domain()}/{label}"])  # -k: kill, then start
