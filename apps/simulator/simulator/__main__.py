from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from simulator.generator import customer_ids, env_float, env_int, make_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("simulator")

TOPIC = os.environ.get("KAFKA_EVENTS_TOPIC", "commerce.events")
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")


def connect_producer() -> KafkaProducer:
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP.split(","),
                acks="all",
                linger_ms=20,
                key_serializer=lambda key: key.encode("utf-8"),
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            )
            log.info("connected to kafka %s topic=%s", BOOTSTRAP, TOPIC)
            return producer
        except NoBrokersAvailable as exc:
            last_error = exc
            log.warning("kafka not ready (attempt %s/30)", attempt)
            time.sleep(2)
    raise RuntimeError(f"could not connect to kafka: {last_error}")


def main() -> None:
    n_customers = env_int("SIMULATOR_CUSTOMERS", 80)
    events_per_sec = env_float("SIMULATOR_EVENTS_PER_SEC", 4.0)
    delay = 1.0 / max(events_per_sec, 0.1)
    customers = customer_ids(n_customers)
    sessions = {cid: str(uuid.uuid4()) for cid in customers}

    producer = connect_producer()
    sent = 0
    log.info("emitting ~%s events/sec for %s customers", events_per_sec, n_customers)

    try:
        while True:
            customer_id = random.choice(customers)
            event = make_event(customer_id, session_id=sessions[customer_id])
            if event["event_type"] == "session_end":
                sessions[customer_id] = str(uuid.uuid4())
            producer.send(TOPIC, key=customer_id, value=event)
            sent += 1
            if sent % 50 == 0:
                producer.flush()
                log.info("sent %s events last_id=%s type=%s", sent, event["event_id"], event["event_type"])
            time.sleep(delay)
    except KeyboardInterrupt:
        log.info("stopping after %s events", sent)
        producer.flush()


if __name__ == "__main__":
    main()
