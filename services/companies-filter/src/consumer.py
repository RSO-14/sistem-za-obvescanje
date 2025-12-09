import pika
import json
import os
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, force=True)
RABBIT_HOST = os.getenv("RABBITMQ_HOST")
RABBIT_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE")
ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY")
QUEUE_NAME = ROUTING_KEY + "_queue"

def start_consumer(on_event_callback):
    def consume_loop():
        while True:
            try:
                logging.info("[RabbitMQ] Connecting as consumer...")

                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=RABBIT_HOST)
                )
                channel = connection.channel()

                # Declare exchange once
                channel.exchange_declare(
                    exchange=RABBIT_EXCHANGE,
                    exchange_type="direct",
                    durable=True
                )

                # Declare queue once
                channel.queue_declare(queue=QUEUE_NAME, durable=True)
                channel.queue_bind(
                    exchange=RABBIT_EXCHANGE,
                    queue=QUEUE_NAME,
                    routing_key=ROUTING_KEY
                )

                logging.info(f"[RabbitMQ] Listening on queue: {QUEUE_NAME}")

                # Consume callback
                def callback(ch, method, properties, body):
                    try:
                        event = json.loads(body)
                        logging.info(f"[RabbitMQ] Received event: {event.get('headline')}")

                        on_event_callback(event)

                        # ACK only if processing succeeded
                        ch.basic_ack(delivery_tag=method.delivery_tag)

                    except Exception as e:
                        logging.error(f"[RabbitMQ] Processing error: {e}")
                        # Safe rejection: requeue = False to avoid infinite loops
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                # Fair dispatch (optional)
                channel.basic_qos(prefetch_count=1)

                channel.basic_consume(
                    queue=QUEUE_NAME,
                    on_message_callback=callback
                )
                channel.start_consuming()

            except pika.exceptions.AMQPError as e:
                logging.error(f"[RabbitMQ] Connection lost: {e}")
            except Exception as e:
                logging.error(f"[RabbitMQ] Unexpected error: {e}")

            logging.info("[RabbitMQ] Reconnecting in 2 seconds...")
            time.sleep(2)

    # Run in background thread so FastAPI doesn’t block
    thread = threading.Thread(target=consume_loop, daemon=True)
    thread.start()