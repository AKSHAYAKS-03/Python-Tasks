import redis

from db import fetch_all_results

from config import REDIS_URL, QUEUE_NAME, DEAD_LETTER_QUEUE



def show_broker_status():
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    pending = r.llen(QUEUE_NAME)
    # len for list
    dead = r.llen(DEAD_LETTER_QUEUE)

    print("=== Broker ===")
    print("[BROKER] Listening on redis://localhost:6379/0")
    print(f'[BROKER] Queue "{QUEUE_NAME}" — {pending} pending')
    print(f"[BROKER] Dead Letter Queue — {dead} tasks\n")

def show_dashboard():
    rows = fetch_all_results()

    print("=== Dashboard ===")
    print("+----------+----------------------+--------------+--------+-----------+")
    print("| Task ID  | Func                 | Status       | Retry  | Duration  |")
    print("+----------+----------------------+--------------+--------+-----------+")

    for row in rows:
        task_id, func_name, status, retries, duration, result, error = row

        short_id = task_id[:8]

        duration_text = f"{duration:.2f}s" if duration is not None else "—"

        print(f"| {short_id:<8} | {func_name:<20} | {status:<12} | {retries:<6} | {duration_text:<9} |")
        # otal width 20 characters irukanum
        # remaining place la spaces fill pannu
    print("+----------+----------------------+--------------+--------+-----------+")



if __name__ == "__main__":
    show_broker_status()
    show_dashboard()