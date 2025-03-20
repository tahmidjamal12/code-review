from flask import Blueprint, send_from_directory

main = Blueprint('main', __name__)

@main.route("/")
def index():
    """Serve the React frontend"""
    return send_from_directory('client/public', 'index.html')

# Serve static files from React build
@main.route("/<path:path>")
def serve_static(path):
    return send_from_directory('client/public', path)