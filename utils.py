import time
import os
from dotenv import load_dotenv
import time
import base64
from PIL import Image
import io
import os
import sys
from seleniumbase import SB
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from PyPDF2 import PdfMerger
from reportlab.pdfgen import canvas
import os
from PyPDF2 import PdfMerger
load_dotenv()

def sign_in(sb):
    # try:
    #     sb.click('a[data-i18n="ao-nav-sign-in"] ',timeout=10)
    # except:
    #     print("Already signed in")
    #     return True
    #read from .env file
    email = os.getenv("email")
    password = os.getenv("password")
    sb.wait_for_element('input[name="username"]',timeout=5000)
    sb.send_keys('input[name="username"]',email)
    sb.send_keys('input[name="password"]',password)
    sb.click('#aoLoginSubmit',timeout=10)
    return True

def create_client(sb,data):
    sb.wait_for_element("#btnClientProfile",timeout=1000)
    sb.click("#btnClientProfile",timeout=10)
    sb.click("span[data-i18n='ao-client-newclient']",timeout=10)
    sb.click("#firstName")
    sb.send_keys("#firstName",data["first_name"])
    sb.click("#lastName")
    sb.send_keys("#lastName",data["last_name"])
    sb.click("#emailAddress")
    sb.send_keys("#emailAddress",data["email"])
    if data["gender"] == "Male":
        sb.click("#genderMale")
    else:
        sb.click("#genderFemale")


    if data["weight_unit"] == "kgs":
        sb.select_option_by_value('select[aria-label="Unit of Weight"]', "kgs")
    else:
        sb.select_option_by_value('select[aria-label="Unit of Weight"]', "lbs")

    sb.send_keys("#weight",data["weight"])

    if data["height_unit"] == "ft": 
        sb.select_option_by_value('select[aria-label="Unit of Height"]', "ft")
    elif data["height_unit"] == "in":
        sb.select_option_by_value('select[aria-label="Unit of Height"]', "in")
    else:
        sb.select_option_by_value('select[aria-label="Unit of Height"]', "cm")
    sb.send_keys("#height",data["height"])
    #make sure format must be like this 1990-05-10 code to convert date to this format
    sb.send_keys("#birthDate",data["date_of_birth"])
    sb.click('button span[data-i18n="ao-nav-save-and-home"]')
    return True


def scan_inner_voice(sb):
    sb.wait_for_element('button span[data-i18n="ao-nav-innervoice"]',timeout=1000)
    sb.click('button span[data-i18n="ao-nav-innervoice"]',timeout=10)
    sb.click('#btnRecord',timeout=10)
    sb.click('button span[data-i18n="ao-innervoice-reports"]',timeout=1000)
    time.sleep(10)   
    return True


def extract_notes(sb):
    sb.wait_for_element(".innervoice-btn-notenofill .mt-1",timeout=1000)
    audio_note_elements = sb.find_elements(".innervoice-btn-notenofill .mt-1")

    # Extract the text content of each note
    notes = [el.text.strip() for el in audio_note_elements]

    print("Extracted notes:", notes)
    sb.wait_for_element(".text-center.my-auto.mx-auto")
    image_note_elements = sb.find_elements(".text-center.my-auto.mx-auto")


    image_notes = [el.text.strip() for el in image_note_elements]

    print("Extracted image notes:", image_notes)
    try:
        image_notes.append(sb.find_element(".mt-2.bg-dark.text-white.mx-auto").text.strip())
    except:
        print("No image notes found")
        pass
    return notes, image_notes





# Note mapping dictionary
NOTE_TO_PATH = {
    "C": "NoteC",
    "C#": "NoteCSharp",
    "D": "NoteD",
    "D#": "NoteDSharp",
    "E": "NoteE",
    "F": "NoteF",
    "F#": "NoteFSharp",
    "G": "NoteG",
    "G#": "NoteGSharp",
    "A": "NoteA",
    "A#": "NoteASharp",
    "B": "NoteB"
}

def download_svg_object(sb, object_id, filename, folder="images"):
    # Make sure the folder exists
    os.makedirs(folder, exist_ok=True)
    
    # Locate the element by its ID
    element = sb.find_element(object_id)
    
    if element:
        sb.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(2)
        file_path_png = os.path.join(folder, f"{filename}.png")
        file_path_pdf = os.path.join(folder, f"{filename}.pdf")
        
        # Take a screenshot of the specific element
        element.screenshot(file_path_png)
        print(f"✅ Saved as PNG: {file_path_png}")
        crop_bottom(file_path_png, 120)
        # Convert PNG to PDF
        image = Image.open(file_path_png)
        image.convert("RGB").save(file_path_pdf)
        print(f"✅ Saved as PDF: {file_path_pdf}")
        
        return file_path_png, file_path_pdf
    else:
        print(f"❌ Element with ID '{object_id}' not found")
        return None, None

    # # Get the SVG content from the embedded <object>
    # svg_content = sb.execute_script(f"""
    #     let obj = document.getElementById("{object_id}");
    #     if (obj && obj.contentDocument) {{
    #         return obj.contentDocument.documentElement.outerHTML;
    #     }} else {{
    #         return null;
    #     }}
    # """)

    # if svg_content:
    #     file_path = os.path.join(folder, filename)
    #     with open(file_path, "w", encoding="utf-8") as f:
    #         f.write(svg_content)
    #     print(f"✅ Saved: {file_path}")
    #     return file_path
    # else:
    #     print(f"❌ Failed to extract SVG from object with ID '{object_id}'")
    #     return None
def crop_bottom(image_path, crop_height):
    # Open the image
    img = Image.open(image_path)
    
    # Get the dimensions of the image
    width, height = img.size
    
    # Calculate the new height after cropping from the bottom
    new_height = height - crop_height
    
    # Crop the image: (left, upper, right, lower)
    cropped_img = img.crop((0, 0, width, new_height))
    
    # Save the cropped image
    cropped_img.save(image_path)
    print(f"✅ Cropped image saved as: {image_path}")



def create_pdf_report(image_folder="images", output_file="report.pdf", notes_order=None):
    # Build the ordered SVG list
    ordered_files = [
        "coverpage.pdf",
        "innervoiceinfo.pdf",
        "howtouse.pdf"
    ]

    if notes_order:
        ordered_files.extend([f"{note.replace('#', 'Sharp')}.pdf" for note in notes_order])
    else:
        ordered_files.extend([f"{note.replace('#', 'Sharp')}.pdf" for note in NOTE_TO_PATH])

    # Convert SVGs to PDFs
    temp_pdfs = []
    for svg_file in ordered_files:
        svg_path = os.path.join(image_folder, svg_file)
        temp_pdfs.append(svg_path)

    # Merge PDFs into a single report
    if temp_pdfs:
        merger = PdfMerger()
        for pdf in temp_pdfs:
            merger.append(pdf)
        merger.write(output_file)
        merger.close()
        print(f"🎉 Final report saved as: {output_file}")
    else:
        print("❌ No PDFs to merge!")

def image_notes_downloader(sb,notes_to_download=None):
    # Using SeleniumBase context manager

    # Always download these common SVGs
    common_svgs = [
        {"id": "#coverpage", "filename": "coverpage"},
        {"id": "#innervoiceinfo", "filename": "innervoiceinfo"},
        {"id": "#howtouse", "filename": "howtouse"}
    ]
    
    print("Downloading common SVGs...")
    for svg_obj in common_svgs:
        download_svg_object(sb, svg_obj["id"], svg_obj["filename"])
    
    # Download specific notes if provided
    if notes_to_download:
        print(f"Downloading specified notes: {', '.join(notes_to_download)}")
        for note in notes_to_download:
            if note in NOTE_TO_PATH:
                note_id = NOTE_TO_PATH[note]
                print(f"Downloading note: {note_id}")
                filename = f"{note.replace('#', 'Sharp')}"
                download_svg_object(sb, f"#{note_id}", filename)
            else:
                print(f"Unknown note: {note}")
    else:
        # Download all available notes
        print("Downloading all available notes...") 
        for note, note_id in NOTE_TO_PATH.items():
            filename = f"{note.replace('#', 'Sharp')}"
            try:
                download_svg_object(sb, f"#{note_id}", filename)
            except Exception as e:
                print(f"Note {note} not found or error: {str(e)}")
    


import requests

# Base URL

import shutil

def get_notes_audio(notes, source_folder="notes_audio"):
    """
    Copy pre-downloaded audio files for the specified notes
    Files are located in backend/notes_audio/ directory
    
    Args:
        notes: List of musical notes (e.g., ['C', 'D#', 'E'])
        source_folder: Folder containing pre-downloaded audio files
    
    Returns:
        List of file paths that were copied
    """
    # Mapping of notes to file names in notes_audio folder
    NOTE_TO_FILENAME = {
        "C": "C.mp3",
        "C#": "C#.mp3",
        "D": "D.mp3",
        "D#": "D#.mp3",
        "E": "E.mp3",
        "F": "F.mp3",
        "F#": "F#.mp3",
        "G": "G.mp3",
        "G#": "G#.mp3",
        "A": "A.mp3",
        "A#": "A#.mp3",
        "B": "B.mp3"
    }
    
    copied_files = []
    
    # Iterate through the list of notes
    for note in notes:
        note = note.upper().replace("♯", "#")  # Handle Unicode sharp symbol if needed
        if note not in NOTE_TO_FILENAME:
            print(f"Note '{note}' not found in mapping.")
            continue

        filename = NOTE_TO_FILENAME[note]
        source_path = os.path.join(source_folder, filename)
        
        # Check if source file exists
        if not os.path.exists(source_path):
            print(f"⚠️  Audio file not found: {source_path}")
            continue
        
        # Copy file to current directory with same name
        destination_path = filename
        
        try:
            shutil.copy2(source_path, destination_path)
            print(f"✅ Copied: {filename}")
            copied_files.append(destination_path)
        except Exception as e:
            print(f"❌ Error copying {filename}: {str(e)}")
    
    return copied_files
