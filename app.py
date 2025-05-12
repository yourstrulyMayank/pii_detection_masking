from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from image import main as process_image
from document import main as process_document
from audio import main as process_audio
from excel import process_excel
from gliner import GLiNER
from logger_utils import setup_logger
from langchain_ollama import OllamaLLM as Ollama
import easyocr
import spacy
import subprocess
import importlib.util
import os
import cv2
import pandas as pd
import threading
import time

# ──────────────────────────────
# Configuration and Initialization
# ──────────────────────────────
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
MASKED_FOLDER = os.path.join(UPLOAD_FOLDER, 'masked')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MASKED_FOLDER, exist_ok=True)

processing_status = {}
logger = setup_logger()

# ──────────────────────────────
# Model Loading
# ──────────────────────────────
def get_gliner_model(local_path="models/gliner_medium-v2.1", model_name="urchade/gliner_medium-v2.1"):
    if os.path.isdir(local_path):
        logger.info(f"Loading GLiNER model from local path: {local_path}")
        return GLiNER.from_pretrained(local_path)
    logger.info(f"Downloading GLiNER model from Hugging Face: {model_name}")
    model = GLiNER.from_pretrained(model_name)
    os.makedirs(local_path, exist_ok=True)
    model.save_pretrained(local_path)
    return model

def get_spacy_model(model_name="en_core_web_sm"):
    if not importlib.util.find_spec(model_name):
        logger.info(f"Downloading SpaCy model: {model_name}")
        subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
    logger.info(f"Loading SpaCy model: {model_name}")
    return spacy.load(model_name)

logger.info("Initializing models...")
gliner_model = get_gliner_model()
spacy_model = get_spacy_model()
reader = easyocr.Reader(['en'], model_storage_directory="./models/easyocr/")
llm_model = Ollama(model="llama3.2")
logger.info("Models initialized successfully.")

# ──────────────────────────────
# Routes
# ──────────────────────────────
@app.route('/')
def index():
    logger.info("Accessed index route.")
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    file = request.files.get('file')
    file_type = request.form.get('file_type')
    labels = request.form.getlist('labels')
    custom_labels = request.form.get('custom_labels', '')

    if custom_labels:
        labels.extend(custom_labels.split(','))

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        logger.info(f"File uploaded: {filename}, Type: {file_type}, Labels: {labels}")

        processing_status[filename] = "processing"

        thread = threading.Thread(target=process_in_background, args=(file_path, labels, file_type, filename))
        thread.start()

        logger.info(f"Started background processing thread for: {filename}")
        return redirect(url_for('processing', filename=filename))
    
    logger.warning("No file received in request.")
    return redirect(url_for('index'))

@app.route('/processing/<filename>')
def processing(filename):
    logger.info(f"Rendering processing page for: {filename}")
    return render_template('processing.html', filename=filename)

@app.route('/check_status/<filename>')
def check_status(filename):
    status = processing_status.get(filename, "processing")
    logger.info(f"Status check for {filename}: {status}")

    if status == "done":
        file_type = processing_status.get(f"{filename}_type", "Unknown")
        original_file_url = '/' + os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/").lstrip('/')
        masked_file_url = '/' + os.path.join(MASKED_FOLDER, filename).replace("\\", "/").lstrip('/')

        if file_type in ['PDF Document', 'Passport', 'Driving License', 'PAN Card', 'Local Card']:
            return jsonify({"status": "done", "redirect": url_for('result_image', filename=filename,
                                                                  original_file_url=original_file_url,
                                                                  masked_file_url=masked_file_url)})
        elif file_type == "Audio":
            text_path = os.path.join(MASKED_FOLDER, f"{filename}.txt")
            with open(text_path, "r", encoding="utf-8") as f:
                redacted_text = f.read()
            return jsonify({"status": "done", "redirect": url_for('result_audio', filename=filename,
                                                                  original_file_url=original_file_url,
                                                                  redacted_text=redacted_text)})
        elif file_type == "Excel File":
            redacted_url = '/' + os.path.join(MASKED_FOLDER, filename.replace(".xlsx", "_redacted.xlsx")).replace("\\", "/").lstrip('/')
            return jsonify({"status": "done",
                            "redirect": url_for('result_excel', filename=filename.replace(".xlsx", "_redacted.xlsx")),
                            "original_file_url": original_file_url,
                            "masked_file_url": redacted_url})
        elif file_type == "Text Document":
            return jsonify({"status": "done", "redirect": url_for('result_text', filename=filename)})
        return jsonify({"status": "error", "message": "Unknown file type"})

    if status == "failed":
        logger.error(f"Processing failed for {filename}")
        return jsonify({"status": "failed", "message": "Processing failed. Please try again."})

    return jsonify({"status": "processing"})

@app.route('/result_image/<filename>')
def result_image(filename):
    logger.info(f"Rendering image result page for: {filename}")
    return render_template('result_image.html',
                           filename=filename,
                           original_file_url=request.args.get('original_file_url', ''),
                           masked_file_url=request.args.get('masked_file_url', ''))

@app.route('/result_audio/<filename>')
def result_audio(filename):
    logger.info(f"Rendering audio result page for: {filename}")
    original_file_url = '/' + os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/").lstrip('/')
    text_path = os.path.join(MASKED_FOLDER, f"{filename}.txt")
    redacted_text = ""
    if os.path.exists(text_path):
        with open(text_path, "r", encoding="utf-8") as f:
            redacted_text = f.read()
    return render_template('result_audio.html', filename=filename,
                           original_file_url=original_file_url,
                           redacted_text=redacted_text)

@app.route('/result_excel/<filename>')
def result_excel(filename):
    logger.info(f"Rendering Excel result page for: {filename}")
    try:
        df = pd.read_excel(os.path.join(MASKED_FOLDER, filename))
        table_html = df.to_html(classes='excel-table', index=False, border=0)
    except Exception as e:
        logger.exception("Error rendering Excel result")
        table_html = ""
    return render_template('result_excel.html', filename=filename, table_html=table_html)

@app.route('/result_text/<filename>')
def result_text(filename):
    logger.info(f"Rendering text result page for: {filename}")
    return render_template('result_text.html', filename=filename)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    logger.info(f"Serving uploaded file: {filename}")
    return send_from_directory(UPLOAD_FOLDER, filename)

# ──────────────────────────────
# Background Processing Function
# ──────────────────────────────
def process_in_background(file_path, labels, file_type, filename):
    logger.info(f"Started processing file: {filename}, Type: {file_type}")
    processing_status[f"{filename}_type"] = file_type

    try:
        time.sleep(2)  # Simulated delay
        processed_file = None

        if file_type in ['PDF Document', 'Passport', 'Driving License', 'PAN Card', 'Local Card']:
            processed_image = process_image(file_path, labels, gliner_model, reader, llm_model, spacy_model)
            if processed_image is not None:
                cv2.imwrite(os.path.join(MASKED_FOLDER, filename), processed_image)
                processed_file = True

        elif file_type == "Audio":
            redacted_text = process_audio(file_path, labels, gliner_model, llm_model, spacy_model)
            with open(os.path.join(MASKED_FOLDER, f"{filename}.txt"), "w", encoding="utf-8") as f:
                f.write(redacted_text)
            processed_file = True

        elif file_type == "Excel File":
            processed_file = process_excel(file_path, labels, gliner_model, llm_model, spacy_model)

        elif file_type == "Text Document":
            processed_file = process_document(file_path)

        if not processed_file:
            raise ValueError("Processing failed")

        processing_status[filename] = "done"
        logger.info(f"Finished processing: {filename}")

    except Exception as e:
        processing_status[filename] = "failed"
        logger.exception(f"Exception occurred while processing {filename}")

# ──────────────────────────────
# Main Entry Point
# ──────────────────────────────
if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(debug=True)
