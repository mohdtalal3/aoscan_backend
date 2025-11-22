from seleniumbase import SB
import time
import os
from utils import *
import json
import sys

def process_form_data(data):
    print(data)
    # Path to your audio file from the form data
    audio_file_path = os.path.abspath(data.get('audio_file', 'file.wav'))

    chrome_args = [
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
        f"--use-file-for-fake-audio-capture={audio_file_path}"
    ]

    # Path to your chrome data directory
    full_path = os.path.abspath("chromedata")
    
    # Initialize the SeleniumBase context manager with Chrome options
    with SB(uc=True, headless=False, chromium_arg=chrome_args, user_data_dir=full_path) as sb:
        # Open the target website
        sb.open("https://app.aoscan.com/AOScanMobileLogin")
        sign_in(sb)
        create_client(sb, data)
        print("opening innervoice")
        scan_inner_voice(sb)
        audio_notes, image_notes = extract_notes(sb)
        print(audio_notes)
        print(image_notes)  
        image_notes_downloader(sb, image_notes)
        create_pdf_report(notes_order=image_notes)
        #download_notes_audio(audio_notes)
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Read form data from command line arguments
        form_data = json.loads(sys.argv[1])
        process_form_data(form_data)
    else:
        print("No form data provided")

#https://app.aoscan.com/AOScanMobileLogin