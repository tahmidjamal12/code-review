from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
import os
import threading
from procopt.server.models import ProcessRun
from procopt.server.pipeline import run_pipeline
from procopt.server.utils import convert_pdf_to_png
from procopt.server.db import db

uploads = Blueprint('uploads', __name__)

@uploads.route("/upload", methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # If it's a PDF, convert to PNG first
            if filename.lower().endswith('.pdf'):
                try:
                    png_path = convert_pdf_to_png(file_path)
                    # Remove the original PDF file
                    os.remove(file_path)
                    file_path = png_path
                except Exception as e:
                    return jsonify({"error": f"Error converting PDF: {str(e)}"}), 500
            
            # Create a new process run
            new_run = ProcessRun(image_path=file_path)
            db.session.add(new_run)
            db.session.commit()
            
            # Start transcription task in background
            thread = threading.Thread(
                target=run_pipeline,
                args=(current_app._get_current_object(), new_run.id, "transcribe")
            )
            thread.start()
            
            return jsonify({
                "status": "success",
                "message": "File uploaded and transcription started",
                "run_id": new_run.id
            })
                
    except Exception as e:
        return jsonify({"error": str(e)}), 500