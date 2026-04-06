# tasks.py

# time module use pannrom delay / work simulate panna
import time

# random module use pannrom some task fail aagura maari test panna
import random


# ---------------------------------------------------------
# TASK 1: Generate Thumbnail
# ---------------------------------------------------------
def generate_thumbnail(image_id, size):
    # small delay kudukrom real work maari feel varanum
    time.sleep(1.5)

    # final output path return panrom
    return f"/thumbs/{image_id}_{size[0]}x{size[1]}.jpg"


# ---------------------------------------------------------
# TASK 2: Send Email
# ---------------------------------------------------------
def send_email(to, template):
    # email send aagura maari simulate pannrom
    time.sleep(1)

    # random ah success / fail aagum
    # retry logic test panna useful
    if random.choice([True, False]):
        raise Exception("SMTPConnectionError")

    # success na result return
    return "email_sent"


# ---------------------------------------------------------
# TASK 3: Generate Report
# ---------------------------------------------------------
def generate_report(report_id):
    # report generate aagura maari small delay
    time.sleep(1)

    # intentionally always fail panrom
    # dead-letter queue test panna
    raise Exception("ReportGenerationError")


# ---------------------------------------------------------
# TASK REGISTRY
# ---------------------------------------------------------
# function object direct Redis la safe ah store panna kashtam
# so function name -> actual function map use panrom
TASK_REGISTRY = {
    "generate_thumbnail": generate_thumbnail,
    "send_email": send_email,
    "generate_report": generate_report
}

# It maps function names to actual Python 
# functions so that workers can execute tasks based on the name received from Redis.