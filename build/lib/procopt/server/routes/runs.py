from flask import Blueprint, current_app, jsonify, request, send_from_directory
from procopt.server.pipeline import run_pipeline
from procopt.server.models import ProcessRun
from procopt.server.db import db
import threading
import os

runs = Blueprint('runs', __name__)

@runs.route("/runs", methods=['GET'])
def list_runs():
    runs = ProcessRun.query.order_by(ProcessRun.created_at.desc()).all()
    result = []
    
    for run in runs:
        result.append({
            "id": run.id,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at
        })
    
    return jsonify(result)

@runs.route("/runs/<int:run_id>/export/<format_type>", methods=['GET'])
def export_run(run_id, format_type):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    
    content = None
    if format_type == "transcription":
        content = run.transcription
    elif format_type == "bottlenecks":
        content = run.bottlenecks
    elif format_type == "improvements":
        content = run.improvements
    else:
        return jsonify({"error": "Invalid format type"}), 400
        
    return jsonify({
        "content": content,
        "filename": f"{format_type}.md"
    })


@runs.route("/runs/<int:run_id>", methods=['GET'])
def get_run(run_id):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
        
    # Only return status if processing is incomplete
    if run.status in ["uploaded", "transcribing", "bottlenecks", "improvements"]:
        return jsonify({
            "status": run.status,
            "id": run.id
        })
    
    # Return full data if processing is complete or failed
    return jsonify({
        "id": run.id,
        "status": run.status,
        "transcription": run.transcription,
        "bottlenecks": run.bottlenecks,
        "improvements": run.improvements
    })

@runs.route("/runs/<int:run_id>/image", methods=['GET'])
def get_run_image(run_id):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    
    # Return the image file
    directory = os.path.dirname(run.image_path)
    filename = os.path.basename(run.image_path)
    return send_from_directory(directory, filename)

@runs.route("/runs/<int:run_id>/transcription", methods=['PUT'])
def update_transcription(run_id):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
        
    data = request.json
    if not data or 'transcription' not in data:
        return jsonify({"error": "Missing transcription data"}), 400
        
    run.transcription = data['transcription']
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Transcription updated successfully"
    })

@runs.route("/runs/<int:run_id>/bottlenecks", methods=['PUT'])
def update_bottlenecks(run_id):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
        
    data = request.json
    if not data or 'bottlenecks' not in data:
        return jsonify({"error": "Missing bottlenecks data"}), 400
        
    run.bottlenecks = data['bottlenecks']
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Bottlenecks updated successfully"
    })

@runs.route("/runs/<int:run_id>/improvements", methods=['PUT'])
def update_improvements(run_id):
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
        
    data = request.json
    if not data or 'improvements' not in data:
        return jsonify({"error": "Missing improvements data"}), 400
        
    run.improvements = data['improvements']
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "Improvements updated successfully"
    })

@runs.route("/runs/<int:run_id>/process/<step>", methods=['POST'])
def run_process_step(run_id, step):
    if step not in ["transcribe", "bottlenecks", "improvements"]:
        return jsonify({"error": "Invalid step"}), 400
        
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    
    # Check prerequisites
    if step == "bottlenecks" and not run.transcription:
        return jsonify({"error": "Transcription must be completed first"}), 400
    if step == "improvements" and not run.bottlenecks:
        return jsonify({"error": "Bottlenecks must be identified first"}), 400
    
    # Start task in background
    thread = threading.Thread(
        target=run_pipeline,
        args=(current_app._get_current_object(), run_id, step)
    )
    thread.start()
    
    return jsonify({
        "status": "processing",
        "message": f"Started {step} processing",
        "run_id": run_id
    })