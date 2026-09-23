from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os


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
        max_wait_time=5
    ) as receiver:
        for msg in receiver:
            print(str(msg))
            receiver.complete_message(msg)
