from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from image import main as process_image
from document import main as process_document
from audio import main as process_audio
# from excel import main as process_excel
# from database import main as process_database
import os
import cv2
import threading
import time
from gliner import GLiNER
import easyocr
import torch
app = Flask(__name__)
# device = "cuda" if torch.cuda.is_available() else "cpu"
device = 'cpu'
if device == 'cuda':
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()
print('device:', device)
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1").to(device)

if device == 'cuda':
    reader = easyocr.Reader(['en'], model_storage_directory="./models/easyocr/", gpu=True)
else:
    reader = easyocr.Reader(['en'], model_storage_directory="./models/easyocr/")


# Folder setup
UPLOAD_FOLDER = 'uploads'
MASKED_FOLDER = os.path.join(UPLOAD_FOLDER, 'masked')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MASKED_FOLDER, exist_ok=True)

processing_status = {}  # Track processing status

@app.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    """Handle file upload and initiate processing."""
    file = request.files.get('file')
    file_type = request.form.get('file_type')
    labels = request.form.getlist('labels')
    custom_labels = request.form.get('custom_labels', '')

    print(f"Received file type: {file_type}")

    if custom_labels:
        labels.extend(custom_labels.split(','))

    if file:
        filename = secure_filename(file.filename)
        original_file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(original_file_path)

        processing_status[filename] = "processing"

        # Start processing in a separate thread
        thread = threading.Thread(target=process_in_background, args=(original_file_path, labels, file_type, filename))
        thread.start()

        return redirect(url_for('processing', filename=filename))

    return redirect(url_for('index'))

@app.route('/processing/<filename>')
def processing(filename):
    """Show processing page while the file is being processed."""
    return render_template('processing.html', filename=filename)

def process_in_background(file_path, labels, file_type, filename):
    """Process the file in the background and update status."""
    print(f'Processing {file_type}: {filename}')
    processing_status[f"{filename}_type"] = file_type
    try:
        time.sleep(2)  # Simulate processing delay

        processed_file = None

        if file_type in ['PDF Document', 'Passport', 'Driving License', 'PAN Card', 'Local Card']:
            print(f'Processing image: {filename}')
            processed_image = process_image(file_path, labels, model, reader)
            if processed_image is not None:
                masked_file_path = os.path.join(MASKED_FOLDER, filename)
                cv2.imwrite(masked_file_path, processed_image)
                processed_file = masked_file_path

        elif file_type == "Audio":
            print(f'Processing audio: {filename}')
            redacted_text = process_audio(file_path, labels, model)
            text_file_path = os.path.join(MASKED_FOLDER, f"{filename}.txt")
            print(f'text_file_path: {text_file_path}')
            with open(text_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(redacted_text)
            processed_file = text_file_path

        # elif file_type == "Excel File":
        #     print(f'Processing Excel file: {filename}')
        #     processed_file = process_excel(file_path)

        # elif file_type == "Database Extract":
        #     print(f'Processing database extract: {filename}')
        #     processed_file = process_database(file_path)

        elif file_type == "Text Document":
            print(f'Processing document: {filename}')
            processed_file = process_document(file_path)

        else:
            raise ValueError("Unsupported file type")

        if processed_file is None:
            raise ValueError(f"Processing failed for {filename}")

        processing_status[filename] = "done"

    except Exception as e:
        print(f"Error processing file {filename}: {e}")
        processing_status[filename] = "failed"

@app.route('/check_status/<filename>')
def check_status(filename):
    """Check processing status and redirect accordingly."""
    status = processing_status.get(filename, "processing")
    
    if status == "done":
        file_type = processing_status.get(f"{filename}_type", "Unknown")
        original_file_url = os.path.join(UPLOAD_FOLDER, filename)
        masked_file_url = os.path.join(MASKED_FOLDER, filename)

        # Ensure paths use forward slashes for URLs
        original_file_url = '/' + original_file_url.replace("\\", "/").lstrip('/')
        masked_file_url = '/' + masked_file_url.replace("\\", "/").lstrip('/')

        if file_type in ['PDF Document', 'Passport', 'Driving License', 'PAN Card', 'Local Card']:
            return jsonify({"status": "done", "redirect": url_for('result_image', filename=filename, 
                                                                  original_file_url=original_file_url, 
                                                                  masked_file_url=masked_file_url)})
        elif file_type == "Audio":
            text_file_path = os.path.join(MASKED_FOLDER, f"{filename}.txt")
            redacted_text = ""
            if os.path.exists(text_file_path):
                with open(text_file_path, "r", encoding="utf-8") as text_file:
                    redacted_text = text_file.read()
            return jsonify({"status": "done", "redirect": url_for('result_audio', filename=filename, original_file_url=original_file_url, redacted_text=redacted_text)})
        elif file_type == "Excel File":
            return jsonify({"status": "done", "redirect": url_for('result_excel', filename=filename)})
        elif file_type == "Database Extract":
            return jsonify({"status": "done", "redirect": url_for('result_database', filename=filename)})
        elif file_type == "Text Document":
            return jsonify({"status": "done", "redirect": url_for('result_text', filename=filename)})
        else:
            return jsonify({"status": "error", "message": "Unknown file type"})

    elif status == "failed":
        return jsonify({"status": "failed", "message": "Processing failed. Please try again."})

    return jsonify({"status": "processing"})


# @app.route('/result')
# def result(filename, file_type):
#     """Redirect to the appropriate result page based on file type."""
#     file_type = request.args.get('file_type')
#     if not file_type:
#         file_type = processing_status.get(f"{filename}_type", "Unknown")
#     original_file_url = os.path.join(UPLOAD_FOLDER, filename)
#     masked_file_url = os.path.join(MASKED_FOLDER, filename)

#     if file_type in ['PDF Document', 'Passport', 'Driving License', 'PAN Card', 'Local Card']:
#         return redirect(url_for('result_image', filename=filename, original_file_url=original_file_url, 
#                                 masked_file_url=masked_file_url))
#     elif file_type == "Audio":
#         return redirect(url_for('result_audio', filename=filename))
#     elif file_type == "Excel File":
#         return redirect(url_for('result_excel', filename=filename))
#     elif file_type == "Database Extract":
#         return redirect(url_for('result_database', filename=filename))
#     elif file_type == "Text Document":
#         return redirect(url_for('result_text', filename=filename))
#     else:
#         return "Unknown file type"

@app.route('/result_image/<filename>')
def result_image(filename):
    """Display result page for image processing."""
    original_file_url = request.args.get('original_file_url', '').lstrip('/')
    masked_file_url = request.args.get('masked_file_url', '').lstrip('/')

    # Ensure paths start with "/"
    original_file_url = '/' + original_file_url
    masked_file_url = '/' + masked_file_url

    return render_template('result_image.html', filename=filename, 
                           original_file_url=original_file_url, 
                           masked_file_url=masked_file_url)


# @app.route('/result_audio/<filename>')
# def result_audio(filename):
#     """Display result page for audio processing."""
#     return render_template('result_audio.html', filename=filename)
@app.route('/result_audio/<filename>')
def result_audio(filename):
    """Display result page for audio processing."""
    original_file_url = os.path.join(UPLOAD_FOLDER, filename)
    text_file_path = os.path.join(MASKED_FOLDER, f"{filename}.txt")
    
    redacted_text = ""
    if os.path.exists(text_file_path):
        with open(text_file_path, "r", encoding="utf-8") as text_file:
            redacted_text = text_file.read()

    return render_template('result_audio.html', filename=filename, 
                           original_file_url="/" + original_file_url.replace("\\", "/").lstrip('/'), 
                           redacted_text=redacted_text)


@app.route('/result_excel/<filename>')
def result_excel(filename):
    """Display result page for Excel file processing."""
    return render_template('result_excel.html', filename=filename)

@app.route('/result_database/<filename>')
def result_database(filename):
    """Display result page for database JSON processing."""
    return render_template('result_database.html', filename=filename)

@app.route('/result_text/<filename>')
def result_text(filename):
    """Display result page for text document processing."""
    return render_template('result_text.html', filename=filename)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


if __name__ == '__main__':
    app.run(debug=True)
