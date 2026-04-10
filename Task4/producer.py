import redis

import json

#  Python object ah binary format ah convert panna
import pickle

# unique task id create panna
import uuid

# current time store panna
from datetime import datetime
from config import REDIS_URL, QUEUE_NAME


class Task:

    def __init__(self, func_name, args=None, kwargs=None, max_retries=3):


        # *args = how many values venalum anuppalam (order important)
        # **kwargs = how many named values venalum anuppalam Idhu name=value format inputs ah edukkum.

        # each task ku unique id create pannrom
        self.id = str(uuid.uuid4())

        self.func_name = func_name

        self.args = args if args else []

        self.kwargs = kwargs if kwargs else {}

        self.status = "PENDING"

        self.retries = 0

        self.max_retries = max_retries

        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # task object ah normal dictionary ah convert panna
    def to_dict(self):
        return {
            "id": self.id,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "status": self.status,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "created_at": self.created_at
        }

    # task ah JSON string ah convert panna
    def to_json(self):
        return json.dumps(self.to_dict())

    # task ah Pickle binary ah convert panna
    def to_pickle(self):
        return pickle.dumps(self.to_dict())

    # print pannumbodhu nice format la kaatka
    def __str__(self):
        return f"<Task id={self.id[:8]} func={self.func_name} status={self.status}>"

class TaskQueue:
    
    def __init__(self):
        # Redis server connect pannrom
        # decode_responses=False because pickle bytes um store panrom So raw format safe ah irukanum
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=False)

    def enqueue(self, func_name, *args, **kwargs):
        # new task create pannrom
        task = Task(func_name, args, kwargs)

        # task ah JSON format ah convert pannrom
        json_data = task.to_json()

        # task ah Pickle format ah convert pannrom
        pickle_data = task.to_pickle()

        # main queue la JSON push pannrom
        self.redis_client.rpush(QUEUE_NAME, json_data)
        # rpush = right side la add pannum  


        # pickle version separate ah Redis hash la save pannrom
        self.redis_client.hset("serialized_tasks", task.id, pickle_data)

        print(f"Task queued: {task}")

        return task


if __name__ == "__main__":
    queue = TaskQueue()

    print("=== Broker ===")
    print("[BROKER] Listening on redis://localhost:6379/0")

    print("\n=== Producer ===")

    queue.enqueue("generate_thumbnail", image_id=4521, size=(256, 256))
    queue.enqueue("send_email", to="bob@co.com", template="welcome")
    queue.enqueue("generate_report", report_id=101)

# Serialization na
# Python object / data-va save panna, send panna, store panna suitable format-ku convert panradhu