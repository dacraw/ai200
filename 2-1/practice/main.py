""" design this inferencx eapi upload lol"""


from flask import Flask, jsonify, request
import uuid
from datetime import timezone, datetime
import json
import os
import logging

LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO')
STORAGE_DIRECTORY=os.getenv('STORAGE_DIRECTORY', '/home/processed')
EMBEDDING_KEY=os.getenv('EMBEDDING_KEY')
ENVIRONMENT=os.getenv('ENVIRONMENT','development')
MAX_DOCUMENT_SIZE_MB=int(os.getenv('MAX_DOCUMENT_SIZE_MB','50'))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - - %(name)s - %(levelname)s - %(message)s"
)
logger=logging.getLogger(__name__)

app=Flask(__name__)

def ensure_storage_directory():
    try:
        os.makedirs(STORAGE_DIRECTORY, exist_ok=True)
        return True
    except Exception as e:
        logger.error("it dont work %s", e)
        return False

def ensure_embedding_key():
    return bool(EMBEDDING_KEY and EMBEDDING_KEY.strip())

@app.route('/')
def root():
    return jsonify({
        "key": EMBEDDING_KEY,
        "environment": ENVIRONMENT
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy'
    }), 200

@app.route('/process', methods=['POST'])
def process_document():
    """process the docmeny basd on input"""

    doc_id=str(uuid.uuid4())
    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "z")

    if not ensure_storage_directory():
        return jsonify({'error','cannot storage info'}),500

    if request.is_json:
        data=request.get_json();
        filename=data.get("filename", "document.txt")
        content=data.get("content", {})
    elif request.files:
        file=request.files.get("file")
        filename=file.filename
        content=file.read().decode('utf-8')
    else:
        filename='document.txt'
        content=request.data.decode('utf-8') or 'Document Info'

    if len(content.encode('utf-8')) / (1024 * 1024) > MAX_DOCUMENT_SIZE_MB:
        return jsonify({'error':f'document to big, max is {MAX_DOCUMENT_SIZE_MB}'})

    keywords=['so','cool','oh wowies']
    result={
        'filename':filename,
        'word_count':len(content.split()),
        'char_count':len(content)
    }

    try:
        filepath=os.path.join(STORAGE_DIRECTORY, f'{doc_id}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        return jsonif({"error":'failed {e}'})

    return jsonify(result)

@app.route('/documents',methods=['GET'])
def list_documents():
    if not ensure_storage_directory():
        return jsonify({'error': 'no storage directory'}),500

    docs=[]
    for filename in os.listdir(STORAGE_DIRECTORY):
        if filename.endswith('.json'):
            filepath=os.path.join(STORAGE_DIRECTORY, filename)
            stat = os.stat(filepath);
            docs.append({
                'doc_id':filename.replace('.json',''),
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
            })

    return jsonify({"results": docs, "count": len(docs)}), 200

@app.route('/documents/<doc_id>',methods=['GET'])
def get_document(doc_id):
    if not ensure_storage_directory():
        return jsonify({'error': 'no storage'}),500

    filepath=os.path.join(STORAGE_DIRECTORY, f"{doc_id}.json")
    try:
        with open(filepath,'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error':f'wahwah {e}'})

if __name__ == "__main__":
    ensure_storage_directory()
    app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT', 8000))
        
    

