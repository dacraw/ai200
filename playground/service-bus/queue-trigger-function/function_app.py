import logging

import azure.functions as func

app = func.FunctionApp()

@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="inference-requests",
    connection="servicebuspractice2645_SERVICEBUS"
)
def process_inference_request(msg: func.ServiceBusMessage):
    logging.info("Processed message: %s", msg.get_body().decode("utf-8"))