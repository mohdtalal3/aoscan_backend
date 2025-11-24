from seleniumbase import SB
import os

# audio_file_path = os.path.abspath(os.path.join("uploads", "Record (online-voice-recorder.com).wav"))
# print(audio_file_path)
audio_file_path=os.path.abspath("file.wav")
print(audio_file_path)
chrome_args = [
    "--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream",
    "--allow-file-access-from-files",
    "--auto-select-desktop-capture-source=default",
    f"--use-file-for-fake-audio-capture=file.wav"
]
# Path to your audio file
full_path = os.path.abspath("chromedata")

# Initialize the SeleniumBase context manager with Chrome options
with SB(headless=False, chromium_arg=chrome_args) as sb:
    # Open the target website
    sb.open("https://online-voice-recorder.com/")
    input("Press Enter to continue...")