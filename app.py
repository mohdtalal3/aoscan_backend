from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
import requests
import json
import subprocess
import queue
import threading

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# Configuration
FRONTEND_UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/uploads'))
BACKEND_TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp_audio')
TEMP_USERS_DIR = os.path.join(os.path.dirname(__file__), 'temp_users')

# Ensure directories exist
os.makedirs(BACKEND_TEMP_DIR, exist_ok=True)
os.makedirs(TEMP_USERS_DIR, exist_ok=True)

# Initialize queue for background processing
request_queue = queue.Queue()
is_processing = False

def process_queue_worker():
    """Background worker to process queued requests one at a time"""
    global is_processing
    
    while True:
        # Get next item from queue (blocks until item is available)
        client_data = request_queue.get()
        
        if client_data is None:  # Poison pill to stop worker
            break
        
        is_processing = True
        print(f"\n{'='*60}")
        print(f"📋 Processing client from queue: {client_data.get('first_name')} {client_data.get('last_name')}")
        print(f"📧 Email: {client_data.get('email')}")
        print(f"🔊 Audio file: {client_data.get('audio_file')}")
        print(f"{'='*60}\n")
        
        try:
            # Call the process_form_data function from main.py
            from main import process_form_data, cleanup_user_folder
            result = process_form_data(client_data)
            
            if result and result.get('success'):
                print(f"\n✅ Successfully processed: {client_data.get('first_name')} {client_data.get('last_name')}\n")
                
                # Send email with attachments
                from email_utils import send_email_with_attachments, update_google_sheet_expire_status
                
                pdf_path = result.get('pdf_path')
                audio_files = result.get('audio_files', [])
                email = result.get('email')
                name = result.get('name')
                user_folder = result.get('user_folder')
                
                print(f"📧 Sending email to {email}...")
                email_sent = send_email_with_attachments(email, name, pdf_path, audio_files)
                
                if email_sent:
                    print(f"✅ Email sent successfully to {email}")
                    
                    # Update Google Sheets to set Expire = TRUE
                    print(f"📝 Updating Google Sheet for {email}...")
                    sheet_updated = update_google_sheet_expire_status(email)
                    
                    if sheet_updated:
                        print(f"✅ Google Sheet updated: Expire set to TRUE for {email}")
                    else:
                        print(f"⚠️  Could not update Google Sheet for {email}")
                    
                    # Cleanup user folder (contains all generated files)
                    print(f"🗑️  Cleaning up user folder...")
                    cleanup_user_folder(user_folder)
                else:
                    print(f"⚠️  Email sending failed for {email}. Files not deleted.")
                    # Don't delete folder if email fails, for manual review
            else:
                # Processing failed
                error_msg = result.get('error', 'Unknown error')
                should_retry = result.get('should_retry', False)
                print(f"\n❌ Processing failed for {client_data.get('first_name')} {client_data.get('last_name')}: {error_msg}\n")
                
                if should_retry:
                    print(f"🔄 Re-queuing {client_data.get('first_name')} {client_data.get('last_name')} for retry...")
                    request_queue.put(client_data)
                    
        except Exception as e:
            print(f"\n❌ Unexpected error processing {client_data.get('first_name')} {client_data.get('last_name')}: {str(e)}\n")
            import traceback
            traceback.print_exc()
            
            # On unexpected error, try to re-queue
            print(f"🔄 Re-queuing {client_data.get('first_name')} {client_data.get('last_name')} due to unexpected error...")
            request_queue.put(client_data)
        
        finally:
            # Clean up: remove the downloaded audio file after processing
            audio_filepath = client_data.get('audio_file')
            if audio_filepath and os.path.exists(audio_filepath):
                try:
                    os.remove(audio_filepath)
                    print(f"🗑️  Temporary audio file removed: {audio_filepath}\n")
                except Exception as e:
                    print(f"⚠️  Could not remove temp file: {str(e)}\n")
            
            # Mark task as done
            request_queue.task_done()
            is_processing = False

# Start background worker thread
worker_thread = threading.Thread(target=process_queue_worker, daemon=True)
worker_thread.start()
print("🔄 Queue worker thread started")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Backend is running'}), 200

@app.route('/submit-client', methods=['POST'])
def submit_client():
    """
    Handle client form submission from frontend
    Expects JSON data with all client fields and audio_url
    Adds to queue and returns immediately
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'first_name', 'last_name', 'email', 'gender', 
            'weight', 'weight_unit', 'height', 'height_unit', 
            'date_of_birth', 'audio_url'
        ]
        
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Extract audio URL
        audio_url = data['audio_url']
        
        # Download audio file from frontend
        try:
            # The audio_url will be something like: http://localhost:5000/uploads/recording_20250101_120000.wav
            # We need to download this file to backend
            print(f"🔽 Attempting to download audio from: {audio_url}")
            response = requests.get(audio_url, timeout=30)
            
            if response.status_code == 200:
                # Generate filename for backend storage
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                audio_filename = f"client_audio_{timestamp}.wav"
                audio_filepath = os.path.join(BACKEND_TEMP_DIR, audio_filename)
                
                # Save audio file
                with open(audio_filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Audio file downloaded: {audio_filepath}")
            else:
                print(f"❌ Failed to download audio. Status: {response.status_code}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to download audio file. Status: {response.status_code}'
                }), 500
        except Exception as e:
            print(f"❌ Error downloading audio from {audio_url}: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error downloading audio: {str(e)}'
            }), 500
        
        # Prepare data for queue processing
        client_data = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'gender': data['gender'],
            'weight': data['weight'],
            'weight_unit': data['weight_unit'],
            'height': data['height'],
            'height_unit': data['height_unit'],
            'date_of_birth': data['date_of_birth'],
            'audio_file': audio_filepath
        }
        
        # Add to queue for background processing
        queue_size = request_queue.qsize()
        request_queue.put(client_data)
        
        print(f"📥 Added to queue: {client_data['first_name']} {client_data['last_name']} (Queue size: {queue_size + 1})")
        
        # Return immediately with 202 Accepted
        return jsonify({
            'success': True,
            'message': 'Your registration has been received and queued for processing',
            'data': {
                'client_name': f"{client_data['first_name']} {client_data['last_name']}",
                'email': client_data['email'],
                'queue_position': queue_size + 1,
                'status': 'queued'
            }
        }), 202  # 202 Accepted - request accepted but not yet processed
        
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/queue-status', methods=['GET'])
def queue_status():
    """Get current queue status"""
    return jsonify({
        'success': True,
        'queue_size': request_queue.qsize(),
        'is_processing': is_processing,
        'status': 'processing' if is_processing else 'idle'
    }), 200

@app.route('/test-connection', methods=['GET'])
def test_connection():
    """Test endpoint to verify backend connectivity"""
    return jsonify({
        'success': True,
        'message': 'Backend connection successful',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    print("🚀 Starting Flask Backend Server...")
    print(f"📁 Frontend uploads directory: {FRONTEND_UPLOADS_DIR}")
    print(f"📁 Backend temp directory: {BACKEND_TEMP_DIR}")
    #app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=False, host='0.0.0.0', port=5000)
