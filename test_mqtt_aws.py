
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import time as t
import json

# Define ENDPOINT, CLIENT_ID, PATH_TO_CERTIFICATE, PATH_TO_PRIVATE_KEY, PATH_TO_AMAZON_ROOT_CA_1, MESSAGE, TOPIC, and RANGE
ENDPOINT = "a1xvyu1lci6ieh-ats.iot.eu-west-3.amazonaws.com"
CLIENT_ID = "testAwsPy"
PATH_TO_CERTIFICATE = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-certificate.pem.crt"
PATH_TO_PRIVATE_KEY = "certificates/1334cda3fa4d4a36ea0a8a7755bdbba76db34541e9f23f89388c83d357d46527-private.pem.key"
PATH_TO_AMAZON_ROOT_CA_1 = "certificates/root.pem"
MESSAGE = "Coucou"
TOPIC = "test/pyAws"
RANGE = 20

# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERTIFICATE,
            pri_key_filepath=PATH_TO_PRIVATE_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_AMAZON_ROOT_CA_1,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6
            )
print("Connecting to {} with client ID '{}'...".format(
        ENDPOINT, CLIENT_ID))
# Make the connect() call
connect_future = mqtt_connection.connect()
# Future.result() waits until a result is available
connect_future.result()
print("Connected!")
# Publish message to server desired number of times.
print('Begin Publish')
for i in range (RANGE):
    data = "{} [{}]".format(MESSAGE, i+1)
    message = {"message" : data}
    mqtt_connection.publish(topic=TOPIC, payload=json.dumps(message), qos=mqtt.QoS.AT_LEAST_ONCE)
    print("Published: '" + json.dumps(message) + "' to the topic: " + TOPIC)
    t.sleep(0.1)
print('Publish End')
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()