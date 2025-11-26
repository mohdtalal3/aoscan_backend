from seleniumbase import SB
import time
import os
from utils import *
import json
import sys
import shutil
from datetime import datetime

def cleanup_user_folder(user_folder):
    """Clean up user-specific temporary folder"""
    try:
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            print(f"🗑️  Cleaned up user folder: {user_folder}")
            return True
    except Exception as e:
        print(f"⚠️  Error cleaning up folder {user_folder}: {str(e)}")
    return False

def process_form_data(data):
    """Process form data with comprehensive error handling and temporary folder management"""
    print(data)
    
    # Create unique user folder for this processing session
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    email_safe = data.get('email', 'unknown').replace('@', '_at_').replace('.', '_')
    user_folder = os.path.abspath(f"temp_users/{email_safe}_{timestamp}")
    images_folder = os.path.join(user_folder, "images")
    
    # Ensure user folder exists
    os.makedirs(images_folder, exist_ok=True)
    print(f"📁 Created user folder: {user_folder}")
    
    # Path to your audio file from the form data
    audio_file_path = os.path.abspath(data.get('audio_file', 'file.wav'))
    
    sb = None
    try:
        chrome_args = [
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            "--allow-file-access-from-files",
            "--auto-select-desktop-capture-source=default",
            f"--use-file-for-fake-audio-capture={audio_file_path}"
        ]

        # Path to your chrome data directory
        full_path = os.path.abspath("chromedata")
        
        print("🌐 Starting browser...")
        # Initialize the SeleniumBase context manager with Chrome options
        with SB(headless=True, chromium_arg=chrome_args, user_data_dir=full_path) as sb:
            # Open the target website
            print("🔐 Opening website and signing in...")
            sb.open("https://app.aoscan.com/AOScanMobileLogin")
            sign_in(sb)
            
            print("👤 Creating client...")
            create_client(sb, data)
            
            print("🎵 Opening inner voice...")
            scan_inner_voice(sb)
            
            print("📝 Extracting notes...")
            audio_notes, image_notes = extract_notes(sb)
            print(f"Audio notes: {audio_notes}")
            print(f"Image notes: {image_notes}")

            print("📥 Downloading images...")
            image_notes_downloader(sb, image_notes, images_folder)
            
            # Generate PDF report with unique filename in user folder
            pdf_filename = f"report_{email_safe}.pdf"
            pdf_path = os.path.join(user_folder, pdf_filename)
            print(f"📄 Creating PDF report: {pdf_path}")
            create_pdf_report(notes_order=image_notes, output_file=pdf_path, image_folder=images_folder)
            
            # Get audio files from pre-downloaded notes_audio folder and copy to user folder
            print("🎵 Getting audio files...")
            audio_files = get_notes_audio(audio_notes, user_folder=user_folder)
        
        print("✅ Processing completed successfully")
        # Return generated file paths and user info for email sending
        return {
            'success': True,
            'pdf_path': pdf_path,
            'audio_files': audio_files if audio_files else [],
            'email': data.get('email'),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}",
            'user_folder': user_folder,
            'images_folder': images_folder
        }
        
    except Exception as e:
        print(f"\n❌ ERROR in process_form_data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up user folder on error
        cleanup_user_folder(user_folder)
        
        # Return error status
        return {
            'success': False,
            'error': str(e),
            'email': data.get('email'),
            'name': f"{data.get('first_name', '')} {data.get('last_name', '')}",
            'user_folder': user_folder,
            'should_retry': True  # Flag to indicate this should be retried
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Read form data from command line arguments
        form_data = json.loads(sys.argv[1])
        process_form_data(form_data)
    else:
        print("No form data provided")

#https://app.aoscan.com/AOScanMobileLogin