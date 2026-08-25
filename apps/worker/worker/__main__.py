from __future__ import annotations

import json
import logging
import os
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from psycopg import OperationalError
from redis.exceptions import RedisError

from worker.db import connect, decode_message, upsert_event
from worker.features import connect_redis, refresh_customer_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

TOPIC = os.environ.get("KAFKA_EVENTS_TOPIC", "commerce.events")
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "churn-flow-worker")


def connect_consumer() -> KafkaConsumer:
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=BOOTSTRAP.split(","),
                group_id=GROUP_ID,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                value_deserializer=lambda raw: raw,
            )
            log.info("consuming %s from %s group=%s", TOPIC, BOOTSTRAP, GROUP_ID)
            return consumer
        except NoBrokersAvailable as exc:
            last_error = exc
            log.warning("kafka not ready (attempt %s/30)", attempt)
            time.sleep(2)
    raise RuntimeError(f"could not connect to kafka: {last_error}")


def connect_db_with_retry():
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            conn = connect()
            log.info("connected to postgres")
            return conn
        except OperationalError as exc:
            last_error = exc
            log.warning("postgres not ready (attempt %s/30)", attempt)
            time.sleep(2)
    raise RuntimeError(f"could not connect to postgres: {last_error}")


def connect_redis_with_retry():
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            client = connect_redis()
            client.ping()
            log.info("connected to redis")
            return client
        except RedisError as exc:
            last_error = exc
            log.warning("redis not ready (attempt %s/30)", attempt)
            time.sleep(2)
    raise RuntimeError(f"could not connect to redis: {last_error}")


def main() -> None:
    conn = connect_db_with_retry()
    redis_client = connect_redis_with_retry()
    consumer = connect_consumer()
    inserted = 0
    duplicates = 0
    try:
        for message in consumer:
            try:
                event = decode_message(message.value)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                log.warning(
                    "skipping invalid event partition=%s offset=%s: %s",
                    message.partition,
                    message.offset,
                    exc,
                )
                consumer.commit()
                continue
            try:
                is_new = upsert_event(conn, event)
                refresh_customer_features(
                    conn,
                    redis_client,
                    customer_id=event["customer_id"],
                    observation_time=event["ts"],
                )
            except Exception:
                conn.rollback()
                log.exception("write failed; not committing kafka offset")
                raise
            if is_new:
                inserted += 1
            else:
                duplicates += 1
            consumer.commit()
            if (inserted + duplicates) % 50 == 0:
                log.info(
                    "ingested new=%s duplicates=%s last_id=%s type=%s customer=%s",
                    inserted,
                    duplicates,
                    event["event_id"],
                    event["event_type"],
                    event["customer_id"],
                )
    except KeyboardInterrupt:
        log.info("stopping new=%s duplicates=%s", inserted, duplicates)
    finally:
        consumer.close()
        conn.close()
        redis_client.close()


if __name__ == "__main__":
    main()
