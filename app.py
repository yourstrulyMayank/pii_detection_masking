from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from text import main as text_masking
from audio import process_audio
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


@app.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_file():
    """Handle file upload and processing."""
    file = request.files.get('file')
    file_type = request.form.get('file_type')
    labels = request.form.getlist('labels')
    custom_labels = request.form.get('custom_labels', '')

    # Combine custom labels with selected labels
    if custom_labels:
        labels.extend(custom_labels.split(','))

    if file:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Process the file based on its type
        if file_type == 'Audio':
            # Process audio file
            original_text, masked_text = process_audio(file_path, labels)
            return render_template(
                'result.html',
                file_type=file_type,
                original=original_text,
                masked=masked_text,
                file_url=filename
            )
        else:
            # Process document file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_text = f.read()

            masked_text = text_masking(original_text, labels)
            return render_template(
                'result.html',
                file_type=file_type,
                original=original_text,
                masked=masked_text
            )

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)