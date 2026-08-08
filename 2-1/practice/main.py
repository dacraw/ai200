"""yo"""


from flask import Flask, request, jsonify
import json
import uuid
from datetime import datetime, timezone
import logging
import os

LOG_LEVEL=os.getenv('LOG_LEVEL','INFO')
ENVIRONMENT=os.getenv('ENVIRONMENT','development')
STORAGE_DIRECTORY=os.getenv('STORAGE_DIRECTORY','/tmp/processed')
EMBEDDING_API_KEY=os.getenv('EMBEDDING_API_KEY')
MAX_DOCUMENT_SIZE_MB=int(os.getenv('MAX_DOCUMENT_SIZE_MB', '50'))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger=logging.getLogger(__name__)

def _ensure_storage_directory():
    try:
        os.makedirs(STORAGE_DIRECTORY,exist_ok=True)
        return True
    except Exception as e:
        return jsonify({'error': 'cannot make storage: {e}'})

def _ensure_embedding_key():
    return bool(EMBEDDING_API_KEY and EMBEDDING_API_KEY.strip())


app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({
        'environment': ENVIRONMENT
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/process', methods=['POST'])
def process_document():
    if not _ensure_storage_directory():
        return jsonify({'error': 'no straoge directory allowed'}),500
    if not _ensure_embedding_key():
        return jsonify({'error': 'no embedding key present in env var'}),500

    doc_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

    if request.is_json:
        data = request.get_json()
        content = data.get('content', {})
        filename = data.get('filename', 'document.txt')
    elif request.files:
        file = request.files.get('file')
        filename = file.filename
        content = file.read().decode('utf-8')
    else:
        content = request.data.decode('utf-8') or "Document yo"
        filename = 'document.txt'

    if not content:
        return jsonify({'error':'there is no content'})

    if len(content.encode('utf-8')) / (1024 * 1024) > MAX_DOCUMENT_SIZE_MB:
        return jsonify({'error': f'document is too big. it is {len(content.encode('utf-8')) / (1024 * 1024)} MB max is {MAX_DOCUMENT_SIZE_MB} MB'})

    result={
        'filename':filename,
        'word_count': len(content.split()),
        'char_count': len(content),
        'timestamp': timestamp
    }

    try:
        filepath =os.path.join(STORAGE_DIRECTORY, f"{doc_id}.json")
        with open(filepath, 'w',encoding='utf-8') as f:
            json.dump(result, f, indent=2)
            result['storage'] = {'saved': True, 'location': filepath}
    except Exception as e:
        return jsonify({'error': 'error writing. {e}'})

    return jsonify(result)

@app.route('/documents')
def list_documents():
    if not _ensure_storage_directory():
        return jsonify({'error':'no storage directory'})

    documents=[]
    for filename in os.listdir(STORAGE_DIRECTORY):
        filepath=os.path.join(STORAGE_DIRECTORY, filename)
        stat = os.stat(filepath)
        documents.append({
            'created_at':datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat().replace('+00:00', 'Z'),
            'size':stat.st_size,
            'doc_id':filename.replace('.json','')
        })

    return jsonify({'documents': documents, 'count': len(documents)})

@app.route('/documents/<doc_id>')
def get_document(doc_id):
    if not _ensure_storage_directory:
        return jsonify({'error':'no storage directory'})

    filepath=os.path.join(STORAGE_DIRECTORY, f'{doc_id}.json')

    if not os.path.exists(filepath):
        return jsonify({'error':'file doesnt exist'})

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
            return jsonify({'error': 'could not open the file . {e}'})


if __name__ == '__main__':
    _ensure_storage_directory()
    _ensure_embedding_key()

    app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT',8000))

    
    