from azure.appconfiguration.provider import load, SettingSelector, WatchKey
from azure.identity import DefaultAzureCredential
import os
import time

endpoint = os.getenv('AZURE_APPCONFIG_ENDPOINT')
credential = DefaultAzureCredential()

# selects = [SettingSelector(key_filter="Pipeline:*", label_filter="Production")]

config = load(
    endpoint=endpoint,
    credential=credential,
    # selects=selects,
    refresh_on=[WatchKey("Sentinel")],
    refresh_interval=5
)

while True:
    config.refresh()
    print(config["OpenAI:Endpoint"])
    time.sleep(5)

# model_endpoint = config["OpenAI:Endpoint"]
# print(model_endpoint)

# batch_size = config["Pipeline:BatchSize"]
# print(batch_size)