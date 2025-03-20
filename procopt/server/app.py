from flask import Flask
import os
from flask_cors import CORS
from procopt.server.routes import main, runs, uploads, chat
from dotenv import load_dotenv
from procopt.server.db import db
load_dotenv()

# Assert OpenAI client is set
if not os.getenv('OPENAI_API_KEY'):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

def create_app():
    app = Flask(__name__, static_folder='client/build')
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(basedir, 'database.sqlite')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(basedir, "uploads"),
    )

    CORS(app)
    db.init_app(app)

    # Register routes
    app.register_blueprint(main)
    app.register_blueprint(runs)
    app.register_blueprint(uploads)
    app.register_blueprint(chat)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
