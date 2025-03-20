from flask import Blueprint, jsonify, request
from procopt.server.db import db
from procopt.server.models import ProcessRun
from procopt.server.llm_utils import MODEL, sys_prompt, call_llm
from typing import List, Dict

chat = Blueprint('chat', __name__)

@chat.route("/chat_response", methods=['POST'])
def chat_response():
    """Chat with the LLM"""
    conversation: List[Dict[str, str]] = request.json['conversation']
    run_id: int = request.json['runId']
    
    # Confirm job exists
    run = db.session.get(ProcessRun, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 200
    
    # Confirm conversation has messages
    if not conversation:
        return jsonify({"error": "No conversation messages sent."}), 200
    if conversation[-1]['role'] != 'user':
        return jsonify({"error": f"Last message must be from user, but was `{conversation[-1]['role']}`"}), 200
    if conversation[-1]['text'] == '':
        return jsonify({"error": "Last message cannot be empty."}), 200
    
    # Get transcribed process map
    transcription = run.transcription # TODO -- fix db lookup
    transcription = '1. Start; 2. Stop; 3. Repeat' # TODO -- dummy

    # Convert conversation to messages
    messages = [
        sys_prompt(' Here is the complete process map that you are analyzing: ' + transcription),
    ] + [
        { 'role' : message['role'], 'content' : message['text'] }
        for message in conversation
    ]
    
    # Call LLM
    response = call_llm(messages=messages, model=MODEL)
    
    return jsonify({ 'text' : response })