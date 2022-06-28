import logging
import os
import json
from json import loads
import boto3
from kafka import KafkaProducer
from kafka import KafkaConsumer

TEST = False

#Kafka is used for logging requests
kafkaDisabled = False

KAFKA_SERVER = os.getenv("FOGPROTECT_KAFKA_SERVER") if os.getenv("FOGPROTECT_KAFKA_SERVER") else "127.0.0.1:9092"
KAFKA_DENY_TOPIC = os.getenv("KAFKA_DENY_TOPIC") if os.getenv("KAFKA_TOPIC") else "blocked-access"
KAFKA_ALLOW_TOPIC = os.getenv("KAFKA_ALLOW_TOPIC") if os.getenv("KAFKA_TOPIC") else "granted-access"
DEFAULT_KAFKA_LOG_TOPIC = 'smart-media'

if TEST:
    DEFAULT_KAFKA_HOST = 'localhost:9092'
else:
    DEFAULT_KAFKA_HOST = 'kafka:9092'
 #   DEFAULT_KAFKA_HOST = 'kafka.fybrik-system:9092'


class KafkaUtils:
    def __init__(self, logger, msgTopic):
        self.kafkaHost = os.getenv("FOGPROTECT_self.kafkaHost") if os.getenv(
            "FOGPROTECT_self.kafkaHost") else DEFAULT_KAFKA_HOST
        self.kafkaLogTopic = os.getenv("SM_self.kafkaLogTopic") if os.getenv("SM_self.kafkaLogTopic") \
            else DEFAULT_KAFKA_LOG_TOPIC
        self.kafkaMsgTopic = os.getenv("SM_self.kafkaLogTopic") if os.getenv("SM_self.kafkaLogTopic") \
            else msgTopic
        self.logger = logger
        self.kafkaDisabled = True
        self.producer = self.connect_to_kafka_producer()
        self.consumer = self.connect_to_kafka_consumer()

    def connect_to_kafka_consumer(self):
        if TEST:
            return
        consumer = None
        try:
            consumer = KafkaConsumer(
                self.kafkaMsgTopic,
                bootstrap_servers=[self.kafkaHost],
                group_id='els',
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: loads(x.decode('utf-8')))
        except:
            raise Exception("Kafka did not connect for host " + self.kafkaHost + " and  topic " + self.kafkaMsgTopic)

        self.logger.info(
            f"Connection to kafka at host " + self.kafkaHost + " and  topic " + self.kafkaMsgTopic + " succeeded!")
        return consumer

    def connect_to_kafka_producer(self):
        global kafkaDisabled
        try:
            producer = KafkaProducer(
                bootstrap_servers=[self.kafkaHost],
                request_timeout_ms=2000
            )  # , value_serializer=lambda x:json.dumps(x).encode('utf-8'))
        except Exception as e:
            self.logger.warning(
                f"\n--->WARNING: Connection to Kafka failed.  Is the server on " + self.kafkaHost + " running?")
            self.logger.warning(e)
            self.kafkaDisabled = True
            return None
        self.kafkaDisabled = False
        self.logger.info(f"Connection to Kafka succeeded! " + self.kafkaHost)
        return (producer)

    def writeToKafka(self, jString):
        if self.kafkaDisabled:
            self.logger.info(f"Kafka topic: " + self.kafkaLogTopic + " log string: " + jString)
            self.logger.warning(f"But kafka is disabled...")
            return None
        jSONoutBytes = str.encode(jString)
        try:
            self.logger.info(f"Writing to Kafka queue " + self.kafkaLogTopic + ": " + jString)
            self.producer.send(self.kafkaLogTopic, value=jSONoutBytes)  # to the SIEM
        except Exception as e:
            self.logger.warning(f"Write to Kafka logging failed.  Is the server on " + self.kafkaLogTopic + " running?")
            self.logger.info(e)
        return None