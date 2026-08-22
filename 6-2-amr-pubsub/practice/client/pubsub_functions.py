import json
import os
import threading
import time
from collections import deque
from datetime import datetime

import redis
from redis_entraid.credential_provider import create_from_default_azure_credential

AVAILABLE_CHANNELS = [
    "orders:created",
    "orders:shipped",
    "inventory:alerts",
    "notifications"
]

def get_client() -> redis.Redis:
    redis_host = os.getenv('REDIS_HOST')

    if not redis_host:
        raise ValueError('need to define redis host')

    credential_provider = create_from_default_azure_credential(
        ("https://redis.azure.com/.default")
    )

    return redis.Redis(
        host=redis_host,
        port=10000,
        credential_provider=credential_provider,
        socket_timeout=30,
        socket_connect_timeout=30,
        ssl=True,
        decode_responses=True
    )

def publish_order_created(r: redis.Redis) -> dict:
    order_data = {
        "event": "order_created",
        "order_id": f"ORD-{datetime.now.strftime("%Y%m%d%H%M%S")}"
    }
    channel = "orders:created"
    subscribers=  r.publish(channel, json.dumps(order_data))

    return {
        "channel": channel,
        "subscribers": subscribers,
        "message": order_data 
    }

def broadcast_to_all(r: redis.Redis) -> dict:
    for channel in AVAILABLE_CHANNELS:
        message = {
            "event": "announcement"
        }
        r.publish(channel, json.dumps(message))


def format_message(message: dict) -> dict:
    timestamp = datetime.now().strftime("%H:%M:%S")
    channel = message.get("channel","unknown")
    pattern = message.get("pattern")

    try:
        data = json.loads(message["data"])
    except (json.JSONDecodeError, TypeError):
        return {
            "timestamp": timestamp
        }


class PubSubManager:
    def __init__(self):
        self.r = get_client()
        self.r.ping()
        self.pubsub = self.r.pubsub(ignore_subscribe_messages=True)