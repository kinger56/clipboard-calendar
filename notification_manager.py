import subprocess


def send_notification(title: str, message: str):
    try:
        title = title.replace('"', '\\"')
        message = message.replace('"', '\\"')

        script = f'display notification "{message}" with title "{title}"'

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        if result.stderr:
            print("Notification Error:", result.stderr)

    except Exception as e:
        print(f"Notification exception: {e}")
