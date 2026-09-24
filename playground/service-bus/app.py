from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os

credential = DefaultAzureCredential()

with ServiceBusClient(
    fully_qualified_namespace=os.getenv("SERVICE_BUS_NAMESPACE"),
    credential=credential
) as client:
    with client.get_queue_sender("inference-requests") as queue_sender:
        queue_sender.send_messages(
            ServiceBusMessage("queue message body")
        )

    with client.get_topic_sender("inference-results") as topic_sender:
        topic_sender.send_messages(
            ServiceBusMessage("topic message body")
        )

with client.get_subscription_receiver(
    topic_name="inference-results",
    subscription_name="notifications",
    max_wait_time=10
) as receiver:
    for msg in receiver:
        print(str(msg))
        receiver.complete_message(msg)