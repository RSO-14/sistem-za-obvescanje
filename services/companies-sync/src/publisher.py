import pika
import json

RABBIT_HOST = "rabbitmq"

def publish_event(event: dict):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBIT_HOST)
        )
        channel = connection.channel()

        channel.queue_declare(queue="new-events", durable=True)

        channel.basic_publish(
            exchange="",
            routing_key="new-events",
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print("RabbitMQ publish:", event["headline"])
        connection.close()
    except Exception as e:
        print(f"RabbitMQ publish error: {e}")
