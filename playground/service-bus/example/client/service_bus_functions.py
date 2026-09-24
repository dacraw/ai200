"""
Service Bus messaging functions for sending, receiving, and routing messages.
These functions serve as the interface between the Flask app and Azure Service Bus.
"""
import os
import json
import uuid
from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusSubQueue
from azure.identity import DefaultAzureCredential

QUEUE_NAME = "inference-requests"
TOPIC_NAME = "inference-results"


def get_client():
    """Get a Service Bus client.

    Uses SERVICE_BUS_CONNECTION_STR (SAS key from the portal) if set,
    otherwise Entra ID authentication against SERVICE_BUS_FQDN.
    """
    conn_str = os.environ.get("SERVICE_BUS_CONNECTION_STR")
    if conn_str:
        return ServiceBusClient.from_connection_string(conn_str)

    fqdn = os.environ.get("SERVICE_BUS_FQDN")

    if not fqdn:
        raise ValueError(
            "SERVICE_BUS_CONNECTION_STR or SERVICE_BUS_FQDN environment variable must be set"
        )

    credential = DefaultAzureCredential()
    return ServiceBusClient(
        fully_qualified_namespace=fqdn,
        credential=credential
    )


# BEGIN SEND MESSAGES FUNCTION



# END SEND MESSAGES FUNCTION


# BEGIN PROCESS MESSAGES FUNCTION



# END PROCESS MESSAGES FUNCTION


# BEGIN INSPECT DLQ FUNCTION



# END INSPECT DLQ FUNCTION


# BEGIN TOPIC MESSAGING FUNCTION



# END TOPIC MESSAGING FUNCTION
