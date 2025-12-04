import pika
import json
import os

RABBIT_HOST = os.getenv("RABBITMQ_HOST")
RABBIT_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE")
ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY")

def publish_event(event: dict):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBIT_HOST)
        )
        channel = connection.channel()

        # 1) Declare exchange
        channel.exchange_declare(
            exchange=RABBIT_EXCHANGE,
            exchange_type="direct",
            durable=True
        )

        # 2) Declare queue
        queue_name = ROUTING_KEY + "_queue"
        channel.queue_declare(queue=queue_name, durable=True)

        # 3) Bind queue -> exchange
        channel.queue_bind(
            exchange=RABBIT_EXCHANGE,
            queue=queue_name,
            routing_key=ROUTING_KEY
        )

        # 4) Publish message
        channel.basic_publish(
            exchange=RABBIT_EXCHANGE,
            routing_key=ROUTING_KEY,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        print("RabbitMQ publish:", event["headline"])
        connection.close()

    except Exception as e:
        print(f"RabbitMQ publish error: {e}")