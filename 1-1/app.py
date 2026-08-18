from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome to flask!"

@app.route('/api/items', methods=["GET"])
def get_items():
    return jsonify([{"id": 1, "name": "bolter"}, {"id": 2, "name": "chainsword"}])

@app.route('/api/items', methods=["POST"])
def create_item():
    data = request.get_json();

    return jsonify(data);



if __name__ == "__main__":
    app.run(debug=True)