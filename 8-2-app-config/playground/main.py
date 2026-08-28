from azure.appconfiguration.provider import load, WatchKey
from azure.identity import DefaultAzureCredential, AzureCliCredential
from featuremanagement import FeatureManager
from flask import Flask, jsonify
import os
import json
import time

endpoint=os.getenv("APP_CONFIG_ENDPOINT")
credential = DefaultAzureCredential()
config = load(
    endpoint=endpoint,
    credential=credential,
    keyvault_credential=credential
)

feature_manager =FeatureManager(config)

# while True:
#     config.refresh()

#     if feature_manager.is_enabled("CoolFeature"):
#         print("Cool Feature is enabled!")
#     else:
#         print("Cool feature disabled")

#     time.sleep(5)
    
app = Flask(__name__)

@app.route('/', methods=["GET"])
def root():
 return jsonify({"secret": config["KeyVaultSecretRef"]})


if __name__ == "__main__":
    app.run(debug=True)