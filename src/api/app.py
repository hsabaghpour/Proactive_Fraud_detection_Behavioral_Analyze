from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
from pathlib import Path
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../../static', static_url_path='')
CORS(app)

# Initialize data storage
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/collect', methods=['POST'])
def collect_behavioral_data():
    """
    Endpoint to collect behavioral biometric data
    Expected payload:
    {
        "session_id": "unique_session_id",
        "timestamp": "iso_timestamp",
        "keystroke_data": {...},
        "mouse_data": {...},
        "device_info": {...}
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Received data collection request for session: {data.get('session_id')}")
        
        # Validate required fields
        required_fields = ['session_id', 'timestamp']
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in request: {required_fields}")
            return jsonify({
                "error": "Missing required fields",
                "required": required_fields
            }), 400
        
        # Store the data
        session_file = DATA_DIR / f"session_{data['session_id']}.json"
        with open(session_file, 'a') as f:
            json.dump(data, f)
            f.write('\n')
        
        logger.info(f"Successfully stored data for session: {data['session_id']}")
        return jsonify({"status": "success", "message": "Data collected successfully"})
    
    except Exception as e:
        logger.error(f"Error in data collection: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_behavior():
    """
    Endpoint to analyze collected behavioral data and return risk assessment
    Expected payload:
    {
        "session_id": "unique_session_id"
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Received analysis request: {data}")
        
        session_id = data.get('session_id')
        if not session_id:
            logger.warning("Missing session_id in analysis request")
            return jsonify({"error": "Missing session_id"}), 400
        
        # Check if we have data for this session
        session_file = DATA_DIR / f"session_{session_id}.json"
        if not session_file.exists():
            logger.warning(f"No data found for session: {session_id}")
            return jsonify({
                "error": "No data found for this session",
                "session_id": session_id
            }), 404
        
        # For demo purposes, generate a random risk score based on session_id
        import random
        risk_score = random.uniform(0, 1)
        confidence = random.uniform(0.7, 1.0)

        # Add some randomization to make the demo more interesting
        unusual_patterns = [
            "irregular typing rhythm",
            "unusual mouse movement patterns",
            "unexpected device characteristics",
            "abnormal input timing",
            "suspicious behavioral patterns"
        ]
        
        normal_patterns = [
            "consistent typing pattern",
            "smooth mouse movements",
            "expected device profile",
            "natural input timing",
            "typical user behavior"
        ]

        # Select factors based on risk score
        if risk_score > 0.7:
            factors = random.sample(unusual_patterns, 3)
        elif risk_score > 0.3:
            factors = random.sample(unusual_patterns, 1) + random.sample(normal_patterns, 2)
        else:
            factors = random.sample(normal_patterns, 3)

        response = {
            "session_id": session_id,
            "risk_score": risk_score,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "factors": factors
        }
        
        logger.info(f"Analysis completed for session {session_id}. Risk score: {risk_score}")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in behavior analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/pipeline')
def pipeline():
    """Serve the pipeline explanation page"""
    return send_from_directory(app.static_folder, 'pipeline.html')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the Behavioral Biometrics Demo server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    args = parser.parse_args()
    
    app.run(debug=True, port=args.port) 