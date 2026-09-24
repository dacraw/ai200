from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusReceiveMode
import os
import json


def get_client():
    """Prefer Entra ID auth; fall back to a SAS connection string."""
    namespace = os.getenv("SERVICE_BUS_NAMESPACE")
    conn_str = os.getenv("SERVICE_BUS_CONNECTION_STR")

    if namespace:
        credential = DefaultAzureCredential()
        try:
            credential.get_token("https://servicebus.azure.net/.default")
            print("Using Entra ID authentication")
            return ServiceBusClient(
                fully_qualified_namespace=namespace,
                credential=credential
            )
        except ClientAuthenticationError:
            if not conn_str:
                raise
            print("Entra ID authentication unavailable, falling back to connection string")

    if conn_str:
        print("Using connection string authentication")
        return ServiceBusClient.from_connection_string(conn_str)

    raise ValueError(
        "Set SERVICE_BUS_NAMESPACE (Entra ID) or SERVICE_BUS_CONNECTION_STR"
    )


with get_client() as client:
    # with client.get_queue_sender("inference-requests") as queue_sender:
    #     queue_sender.send_messages(
    #         ServiceBusMessage("queue message body")
    #     )

    # with client.get_queue_receiver(
    #     queue_name="inference-requests",
    #     receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    #     max_wait_time=5
    # ) as queue_receiver:
    #     for msg in queue_receiver:
    #         try:
    #             print(msg)
    #             queue_receiver.complete_message(msg)
    #         except json.JSONDecodeError:
    #             queue_receiver.dead_letter_message(
    #                 msg,
    #                 reason="MalformedPayload",
    #                 error_description="Message body is not valid JSON"
    #             )
    #         except Exception as e:
    #             queue_receiver.dead_letter_message(
    #                 msg,
    #                 reason="Exception",
    #                 error_description=e
    #             )

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
    with client.get_subscription_receiver(
        topic_name="inference-results",
        subscription_name="notifications",
        max_wait_time=5
    ) as receiver:
        for msg in receiver:
            print(str(msg))
            receiver.complete_message(msg)
