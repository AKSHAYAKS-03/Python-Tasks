
import queue

import redis

import json

import time

# command line argument read panna import
import sys


from tasks import TASK_REGISTRY

from db import init_db, save_result
from config import REDIS_URL, QUEUE_NAME, DEAD_LETTER_QUEUE

def get_redis():
    # decode_responses=True because JSON strings ah read panrom
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def worker_process(worker_id):
    r = get_redis()

    print(f"[WORKER-{worker_id}] Connected and waiting for tasks...")

    while True:
        # BLPOP = blocking left pop
        # # queue la item irundha eduthu # illa na wait pannu
        task_data = r.blpop(QUEUE_NAME, timeout=5)

        if not task_data:
            continue

        # task_data usually tuple maari varum:
        # (queue_name, actual_task_json)
        _, raw_task = task_data

        # JSON string ah dictionary ah convert pannrom
        task = json.loads(raw_task)

        task_id = task["id"]
        func_name = task["func_name"]
        args = task["args"]
        kwargs = task["kwargs"]
        retries = task["retries"]
        max_retries = task["max_retries"]

        print(f"\n[WORKER-{worker_id}] Picked up task {task_id[:8]} ({func_name})")

        func = TASK_REGISTRY.get(func_name)

        if not func:
            print(f"[WORKER-{worker_id}] Unknown task function: {func_name}")
            continue

        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            duration = time.time() - start_time

            print(f"[WORKER-{worker_id}] Task {task_id[:8]} completed in {duration:.2f}s — result: {result}")

            save_result(
                task_id,
                func_name,
                "SUCCESS",
                retries,
                duration,
                str(result),
                None
            )

            r.publish("task_updates", f"{task_id}:SUCCESS")

        except Exception as e:
            retries += 1

            if retries > max_retries:
                print(f"[WORKER-{worker_id}] Task {task_id[:8]} permanently FAILED ({e}) — moved to dead letter queue")

                task["retries"] = retries
                task["status"] = "DEAD_LETTER"

                r.rpush(DEAD_LETTER_QUEUE, json.dumps(task))

                save_result(
                    task_id,
                    func_name,
                    "DEAD_LETTER",
                    retries,
                    None,
                    None,
                    str(e)
                )

                r.publish("task_updates", f"{task_id}:DEAD_LETTER")

            else:
                # exponential backoff
                # retry 1 -> 2 sec
                # retry 2 -> 4 sec
                # retry 3 -> 8 sec
                delay = 2 ** retries

                print(f"[WORKER-{worker_id}] Task {task_id[:8]} FAILED ({e}) — retry {retries}/{max_retries} in {delay}s")

                time.sleep(delay)

                task["retries"] = retries
                task["status"] = "RETRYING"

                r.rpush(QUEUE_NAME, json.dumps(task))

                r.publish("task_updates", f"{task_id}:RETRYING")


if __name__ == "__main__":
    init_db()

    worker_id = 1

    # example: python worker.py 2
    if len(sys.argv) > 1:
        worker_id = sys.argv[1]

    worker_process(worker_id)


    