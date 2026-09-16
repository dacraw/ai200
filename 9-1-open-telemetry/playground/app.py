from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.trace import SpanKind
import requests
import os
from flask import Flask, jsonify, render_template, flash

print(os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"))

configure_azure_monitor(
    resource=Resource.create({
        "service.name":"embedding-service",
        "service.namespace":"rag-pipeline",
        "service.instance.id":"embedding-instance-1"
    })
)

tracer = trace.get_tracer("embedding-service")

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def home():
    with tracer.start_as_current_span("GenerateEmbedding") as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        return jsonify({"status": "healthy"}), 200
    
@app.route('/kind/server')
def kind_server():
    with tracer.start_as_current_span("GenerateEmbedding", kind=SpanKind.SERVER) as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        flash("Triggered server kind. Check requests.")

        return render_template("index.html")
    
@app.route('/kind/client')
def kind_client():
    with tracer.start_as_current_span("GenerateEmbedding", kind=SpanKind.CLIENT) as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        return jsonify({"status": "healthy"}), 200
    
@app.route('/kind/internal')
def kind_internal():
    with tracer.start_as_current_span("GenerateEmbedding", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        return jsonify({"status": "healthy"}), 200
    
@app.route('/kind/producer')
def kind_producer():
    with tracer.start_as_current_span("GenerateEmbedding", kind=SpanKind.PRODUCER) as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        return jsonify({"status": "healthy"}), 200
    
@app.route('/kind/consumer')
def kind_consumer():
    with tracer.start_as_current_span("GenerateEmbedding", kind=SpanKind.CONSUMER) as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.token_count", 12)
        requests.get("https://jsonplaceholder.typicode.com/todos/1")

        return jsonify({"status": "healthy"}), 200

 
if __name__ == "__main__":
    app.run(debug=True, port=80, host="0.0.0.0")