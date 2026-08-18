from flask import Flask, jsonify, request
import uuid
from datetime import datetime, timezone
import logging
import json
import os

LOG_LEVEL=os.getenv("LOG_LEVEL","INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
MAX_DOCUMENT_SIZE_MB = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
STORAGE_DIRECTORY = os.getenv("STORAGE_DIRECTORY", "/home/processed")
PORT = int(os.getenv("PORT", 80))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def ensure_storage_directory():
    try:
        os.makedirs(STORAGE_DIRECTORY, exist_ok=True)
        return True
    except Exception as e:
        logger.error("{e}")
        return False

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "environment": ENVIRONMENT
    })

@app.route('/process', methods=['POST'])
def process_document():
    if not ensure_storage_directory():
        return jsonify({"error": "cannot store since ther is no storage directory!"}), 500

    logger.info("processing..")
    doc_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    if request.is_json:
        data = request.get_json();
        content = data.get("content", "")
        filename = data.get("filename", "")
    elif request.files:
        file = request.files.get("file")
        if file:
            content = file.read().decode("utf-8", errors="ignore")
            filename = file.filename
        else:
            return jsonify({"error": "there is no file!!"})
    else:
        content = request.data.decode('utf-8', errors="ignore") or "Sample Document"
        filename = "document.txt"

    if len(content.encode('utf-8')) / (1024 * 1024) > MAX_DOCUMENT_SIZE_MB:
        return jsonify({"error": "it too big"}), 400



    try:
        logger.info(f'tryign to save the file {filename}')
        logger.info(f'save location is {STORAGE_DIRECTORY}')
        filepath = os.path.join(STORAGE_DIRECTORY, f"{doc_id}.json")
        with open(filepath, 'w') as f:
            logger.info('in the write directory')
            json.dump(content, f, indent=2)
            logger.info('completed json dump')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    result = {
        "doc_id": doc_id,
        "filename": filename,
        "word_count": len(content.split()),
        "char_count": len(content),
        "timestamp": timestamp
    }

    return jsonify(result), 200

@app.route('/documents', methods=['GET'])
def list_documents():
    if not ensure_storage_directory():
        return jsonify({"error": "no storage"}), 500

    try:
        files = []
        for filename in os.listdir(STORAGE_DIRECTORY):
            logger.info(f'iterating with {filename}')
            if filename.endswith('.json'):
                logger.info(f'the filename {filename} ends with .json')
                filepath = os.path.join(STORAGE_DIRECTORY, filename)
                stat = os.stat(filepath);
                logger.info(f'logging {filename}')
                files.append({
                    "document_id": filename.replace(".json", ""),
                    "content_bytes": stat.st_size,
                    "created_date": datetime.fromtimestamp(stat.st_ctime),
                })
    except Exception as e:
        return jsonify({"error": f"errorrrrrr {e}"})

    return jsonify({"files": files, "count": len(files)});

@app.route('/documents/<doc_id>')
def get_document(doc_id):
    if not ensure_storage_directory():
        return jsonify({"error":"no storage.."}), 500

    filepath = os.path.join(STORAGE_DIRECTORY, f"{doc_id}.json")

    if not os.path.exists(filepath):
        return jsonify({'error':'the fil doesn not exist'}), 500


    with open(filepath, 'r') as f:
        file = json.load(f)

    return jsonify(file)

if __name__ == "__main__":
    ensure_storage_directory();

    app.run(host="0.0.0.0", port=PORT, debug=True)

    

       
        
        