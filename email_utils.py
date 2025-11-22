import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import json

load_dotenv()

# Email Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

# Google Sheets Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
CREDENTIALS_JSON = os.getenv('CREDENTIALS_JSON')


def send_email_with_attachments(recipient_email, client_name, pdf_path, audio_files):
    """
    Send email with PDF report and audio files attached
    
    Args:
        recipient_email: Email address of the recipient
        client_name: Name of the client
        pdf_path: Path to the PDF report
        audio_files: List of paths to audio files
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"Your AO Scan Reports - {client_name}"
        
        # Email body
        body = f"""
Dear {client_name},

Thank you for using our AO Scan service!

We are pleased to provide you with your personalized scan reports. Please find attached:

📄 **Complete AO Scan Report (PDF)** - Your comprehensive scan results and analysis
🎵 **Audio Healing Frequencies (MP3)** - Personalized healing tones based on your scan

**How to Use Your Audio Files:**
Listen to the provided audio frequencies for 15-20 minutes daily. These frequencies are specifically calibrated to your unique energetic signature and are designed to support your body's natural healing processes.

**Important Notes:**
- Your access to the scanning system has now been marked as complete
- If you need another scan in the future, please reach out to renew your access
- Keep these files in a safe place for your records

If you have any questions about your results or how to use your healing frequencies, please don't hesitate to contact us.

Wishing you health and wellness,

The AO Scan Team

---
This is an automated message. Please do not reply to this email.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF report
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(pdf_path)}"')
                msg.attach(part)
            print(f"✅ Attached PDF: {pdf_path}")
        
        # Attach audio files
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                with open(audio_file, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(audio_file)}"')
                    msg.attach(part)
                print(f"✅ Attached audio: {audio_file}")
        
        # Send email
        print(f"📧 Sending email to {recipient_email}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False


def update_google_sheet_expire_status(email):
    """
    Update the Expire status to TRUE for the given email in Google Sheets
    
    Args:
        email: Email address of the user
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse JSON string from environment variable
        creds_dict = json.loads(CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Find the row with the matching email
        cell = sheet.find(email, in_column=3)  # Column 3 is Email (A=1, B=2, C=3)
        
        if cell:
            # Update the Expire column (column 4: D) to TRUE
            sheet.update_cell(cell.row, 4, 'TRUE')
            print(f"✅ Updated Google Sheet: Set Expire=TRUE for {email}")
            return True
        else:
            print(f"⚠️  Email {email} not found in Google Sheet")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Google Sheet: {str(e)}")
        return False


def cleanup_generated_files(pdf_path, audio_files, images_folder='images'):
    """
    Delete all generated files after sending email
    
    Args:
        pdf_path: Path to the PDF report
        audio_files: List of paths to audio files
        images_folder: Folder containing generated images
    
    Returns:
        bool: True if cleanup was successful
    """
    try:
        # Delete PDF
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"🗑️  Deleted PDF: {pdf_path}")
        
        # Delete audio files
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                os.remove(audio_file)
                print(f"🗑️  Deleted audio: {audio_file}")
        
        # Delete images folder and all contents
        if os.path.exists(images_folder):
            import shutil
            shutil.rmtree(images_folder)
            print(f"🗑️  Deleted images folder: {images_folder}")
        
        print("✅ Cleanup completed successfully")
        return True
        
    except Exception as e:
        print(f"⚠️  Error during cleanup: {str(e)}")
        return False
