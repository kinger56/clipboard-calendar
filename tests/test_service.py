"""Start/Stop must go through launchd, by label, never by killing processes."""

import os
import subprocess

import service


class FakeLaunchctl:
    def __init__(self, loaded=True, state="running"):
        self.loaded = loaded
        self.state = state
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "print":
            out = f"state = {self.state}\n" if self.loaded else ""
            return subprocess.CompletedProcess(args, 0 if self.loaded else 113, out, "")
        return subprocess.CompletedProcess(args, 0, "", "")


DOMAIN = f"gui/{os.getuid()}"
TARGET = f"{DOMAIN}/{service.ASSISTANT_LABEL}"


def test_is_running():
    assert service.is_running(run=FakeLaunchctl(state="running"))
    assert not service.is_running(run=FakeLaunchctl(state="not running"))
    assert not service.is_running(run=FakeLaunchctl(loaded=False))


def test_stop_unloads_the_service_so_keepalive_cannot_restart_it():
    run = FakeLaunchctl()
    service.stop(run=run)
    assert run.calls == [["bootout", TARGET]]


def test_start_loads_a_stopped_service():
    run = FakeLaunchctl(loaded=False)
    service.start(run=run)
    plist = os.path.join(service.LAUNCH_AGENTS, f"{service.ASSISTANT_LABEL}.plist")
    assert run.calls[-1] == ["bootstrap", DOMAIN, plist]


def test_start_kicks_an_already_loaded_service():
    run = FakeLaunchctl(loaded=True, state="not running")
    service.start(run=run)
    assert run.calls[-1] == ["kickstart", TARGET]


def test_restart_kills_then_starts():
    run = FakeLaunchctl()
    service.restart(run=run)
    assert run.calls == [["kickstart", "-k", TARGET]]


def test_menu_never_kills_processes_by_name():
    source = open(os.path.join(os.path.dirname(service.__file__), "menu_app.py")).read()
    assert "pkill" not in source and "os.system" not in source


def test_install_scripts_use_the_same_labels_as_the_menu():
    # If these drift apart, Start/Stop would control a service that doesn't exist.
    root = os.path.dirname(service.__file__)
    for script in ("install.sh", "uninstall.sh"):
        text = open(os.path.join(root, script)).read()
        assert service.ASSISTANT_LABEL in text
        assert service.MENU_LABEL in text
