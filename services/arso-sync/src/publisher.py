import pika
import json
import os
import time

RABBIT_HOST = os.getenv("RABBITMQ_HOST")
RABBIT_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE")
ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY")

connection = None
channel = None

def get_channel():
    global connection, channel

    if channel and channel.is_open:
        return channel

    # Create new connection
    for attempt in range(5):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBIT_HOST)
            )
            channel = connection.channel()

            # Durable exchange
            channel.exchange_declare(
                exchange=RABBIT_EXCHANGE,
                exchange_type="direct",
                durable=True
            )

            # Enable publisher confirms
            channel.confirm_delivery()
            return channel

        except Exception as e:
            print(f"[RabbitMQ] Connect failed (attempt {attempt+1}): {e}")
            time.sleep(1)

    raise RuntimeError("Cannot connect to RabbitMQ")

def publish_event(event: dict):
    body = json.dumps(event)

    try:
        ch = get_channel()

        ch.basic_publish(
            exchange=RABBIT_EXCHANGE,
            routing_key=ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2  # Persistent
            ),
            mandatory=True,
        )
        print("[RabbitMQ] Published:", event["headline"])

    except pika.exceptions.UnroutableError:
        print("[RabbitMQ] Message was unroutable → LOST")

    except Exception as e:
        print(f"[RabbitMQ] Publish error: {e}")