import rumps
import subprocess
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def kill_all_assistants():
    os.system("pkill -f main.py")  # ✅ kills ALL instances


class ClipboardAssistantApp(rumps.App):

    def __init__(self):
        super().__init__("🔴📋", quit_button=None)

        self.menu = [
            "Start Assistant",
            "Stop Assistant",
            "Restart Assistant",
            None,
            "Show Upcoming Events",
            "Clear Memory",
            None,
            "Quit"
        ]

        self.is_running = False

    def update_status(self):
        self.title = "🟢📋" if self.is_running else "🔴📋"

    def start_assistant(self):
        if not self.is_running:
            kill_all_assistants()  # ✅ prevent duplicates

            subprocess.Popen(
                ["python3", "main.py"],
                cwd=BASE_DIR
            )

            self.is_running = True
            self.update_status()
            rumps.notification("Assistant", "Started", "")
        else:
            rumps.notification("Assistant", "Already Running", "")

    def stop_assistant(self):
        kill_all_assistants()  # ✅ KILL EVERYTHING

        self.is_running = False
        self.update_status()

        rumps.notification("Assistant", "Stopped COMPLETELY", "")

    def restart_assistant(self):
        kill_all_assistants()

        subprocess.Popen(
            ["python3", "main.py"],
            cwd=BASE_DIR
        )

        self.is_running = True
        self.update_status()
        rumps.notification("Assistant", "Restarted", "")

    def show_events(self, _):
        subprocess.Popen(["python3", "main.py"])  # uses your existing logic

    def clear_memory(self, _):
        try:
            file_path = os.path.join(BASE_DIR, "processed_events.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                rumps.notification("Memory Cleared", "", "")
        except:
            rumps.notification("Error", "Could not clear memory", "")

    def quit_app(self, _):
        kill_all_assistants()
        rumps.quit_application()

    @rumps.clicked("Start Assistant")
    def on_start(self, _):
        self.start_assistant()

    @rumps.clicked("Stop Assistant")
    def on_stop(self, _):
        self.stop_assistant()

    @rumps.clicked("Restart Assistant")
    def on_restart(self, _):
        self.restart_assistant()

    @rumps.clicked("Show Upcoming Events")
    def on_events(self, sender):
        self.show_events(sender)

    @rumps.clicked("Clear Memory")
    def on_clear(self, sender):
        self.clear_memory(sender)

    @rumps.clicked("Quit")
    def on_quit(self, sender):
        self.quit_app(sender)


if __name__ == "__main__":
    ClipboardAssistantApp().run()