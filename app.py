from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from image import main as image_masking  # Import image processing function
import os
import cv2
import threading
import time
from gliner import GLiNER
import easyocr
import shutil  # For moving files

app = Flask(__name__)
model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
reader = easyocr.Reader(['en'])

# Folder setup
UPLOAD_FOLDER = 'uploads'
PROCESSING_FOLDER = os.path.join(UPLOAD_FOLDER, 'processing')
MASKED_FOLDER = os.path.join(UPLOAD_FOLDER, 'masked')
PROCESSED_FOLDER = 'processed'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSING_FOLDER, exist_ok=True)
os.makedirs(MASKED_FOLDER, exist_ok=True)

processing_status = {}  # Dictionary to track processing status


@app.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_file():
    """Handle file upload and start processing asynchronously."""
    file = request.files.get('file')
    file_type = request.form.get('file_type')
    labels = request.form.getlist('labels')
    custom_labels = request.form.get('custom_labels', '')

    # Combine custom labels with selected labels
    if custom_labels:
        labels.extend(custom_labels.split(','))
    print(labels)

    if file:
        filename = secure_filename(file.filename)
        
        # Save the original file directly to the uploads folder
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
    try:
        time.sleep(2)  # Simulate processing delay

        if file_type in ['Document', 'Passport', 'PAN Card', 'Others']:
            print('Masking Image')
            processed_image = image_masking(file_path, labels, model, reader)

            if processed_image is None:
                raise ValueError("Image processing returned None.")

            # Save masked image inside 'uploads/masked'
            masked_file_path = os.path.join(MASKED_FOLDER, filename)
            cv2.imwrite(masked_file_path, processed_image)

            processing_status[filename] = "done"
        else:
            processing_status[filename] = "failed"
    except Exception as e:
        print(f"Error processing file {filename}: {e}")
        processing_status[filename] = "failed"


@app.route('/check_status/<filename>')
def check_status(filename):
    status = processing_status.get(filename, "processing")
    print(f"Status for {filename}: {status}")  # Debugging log
    if status == "done":
        return redirect(url_for('result', filename=filename))
    elif status == "failed":
        return "Processing failed. Please try again."
    return "Processing..."


@app.route('/result')
def result(filename):
    """Show the result page with processed file."""
    original_file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    masked_file_url = os.path.join(MASKED_FOLDER, filename)
    return render_template('result.html', original_file_url=original_file_url, masked_file_url=masked_file_url)


if __name__ == '__main__':
    app.run(debug=True)
