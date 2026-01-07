import pika
import json
import os
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, force=True)
RABBIT_HOST = os.getenv("RABBITMQ_HOST")
RABBIT_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE")
ROUTING_KEYS = [
    k.strip()
    for k in os.getenv("RABBITMQ_ROUTING_KEYS", "").split(",")
    if k.strip()
]
QUEUE_NAME = "events_queue"

if not ROUTING_KEYS:
    raise RuntimeError("RABBITMQ_ROUTING_KEYS is not set")

def start_consumer(on_event_callback):
    def consume_loop():
        while True:
            try:
                logging.info("[RabbitMQ] Starting consumer...")
                logging.info(f"[RabbitMQ] Routing keys: {ROUTING_KEYS}")

                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=RABBIT_HOST)
                )
                channel = connection.channel()

                # Exchange (idempotent)
                channel.exchange_declare(
                    exchange=RABBIT_EXCHANGE,
                    exchange_type="direct",
                    durable=True
                )

                # Queue (idempotent)
                channel.queue_declare(
                    queue=QUEUE_NAME,
                    durable=True
                )

                # Bind queue na VSE routing key-e
                for key in ROUTING_KEYS:
                    channel.queue_bind(
                        exchange=RABBIT_EXCHANGE,
                        queue=QUEUE_NAME,
                        routing_key=key
                    )
                    logging.info(f"[RabbitMQ] Bound queue '{QUEUE_NAME}' → '{key}'")

                # Fair dispatch
                channel.basic_qos(prefetch_count=1)

                def callback(ch, method, properties, body):
                    try:
                        event = json.loads(body)
                        rk = method.routing_key

                        logging.info(
                            f"[RabbitMQ] Received ({rk}): {event.get('headline')}"
                        )

                        # Predaj event aplikaciji
                        on_event_callback(event, rk)

                        ch.basic_ack(delivery_tag=method.delivery_tag)

                    except Exception as e:
                        logging.error(f"[RabbitMQ] Processing error: {e}")
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=False
                        )

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