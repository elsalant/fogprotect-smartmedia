import os
from json import loads
from kafka import KafkaProducer
from kafka import KafkaConsumer
import logging
TEST = False
kafka_already_connected = False

logger = logging.getLogger('kafka_utils.py')
logger.setLevel(logging.DEBUG)

KAFKA_SERVER = os.getenv("FOGPROTECT_KAFKA_SERVER") if os.getenv("FOGPROTECT_KAFKA_SERVER") else "172.31.35.158:9092"
if TEST:
    KAFKA_SERVER = 'localhost:9092'
DEFAULT_KAFKA_LOG_TOPIC = 'smart-media'

class KafkaUtils:
    def __init__(self):
        self.kafkaHost = os.getenv("FOGPROTECT_self.kafkaHost") if os.getenv("FOGPROTECT_self.kafkaHost") else KAFKA_SERVER
        self.kafkaDisabled = False
        self.producer = None
#        self.producer = self.connect_to_kafka_producer()
 #       self.consumer = self.connect_to_kafka_consumer('NOTUSED')
        logger.info('KafkaUtils initiated!')

    def connect_to_kafka_consumer(self, msgTopic):
        if TEST:
            return
        consumer = None
        try:
            consumer = KafkaConsumer(
                msgTopic,
                bootstrap_servers=[self.kafkaHost],
                group_id='els',
                auto_offset_reset='earliest',  # lastest
                enable_auto_commit=True,
                value_deserializer=lambda x: loads(x.decode('utf-8')))
        except:
            debugLine= "Kafka did not connect for host " + str(self.kafkaHost) + " and  topic " + str(msgTopic)
            logger.info(debugLine)
            self.kafkaDisabled = True
        logger.info(
            f"Connection to kafka at host " + self.kafkaHost + " and  topic " + msgTopic + " succeeded!")
        return consumer

    def connect_to_kafka_producer(self):
        global kafka_already_connected
        try:
            producer = KafkaProducer(
                bootstrap_servers=[self.kafkaHost],
                request_timeout_ms=10000
            )  # , value_serializer=lambda x:json.dumps(x).encode('utf-8'))
            kafka_already_connected = True
        except Exception as e:
            logger.warning(
                f"\n--->WARNING: Connection to Kafka failed for producer.  Is the server on " + self.kafkaHost + " running?")
            logger.warning(e)
            self.kafkaDisabled = True
            return None
        self.kafkaDisabled = False
        logger.info(f"Connection to Kafka succeeded! " + self.kafkaHost)
        self.producer = producer
        return (producer)

    def writeToKafka(self, jString, logTopic):
        if not kafka_already_connected and not self.kafkaDisabled:
            producer = self.connect_to_kafka_producer()
        if self.kafkaDisabled:
            logger.info(f"Kafka topic: " + logTopic + " log string: " + jString)
            logger.warning(f"But kafka is disabled...")
            return None
        jSONoutBytes = str.encode(jString)
        try:
            logger.info(f"Writing to Kafka queue " + logTopic + ": " + jString)
            self.producer.send(logTopic, value=jSONoutBytes)
        except Exception as e:
            logger.warning(f"Write to Kafka logging failed.  Is the server on " + logTopic + " running?")
            logger.info(e)
        return None