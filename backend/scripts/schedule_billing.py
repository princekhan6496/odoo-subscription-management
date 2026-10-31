"""Create the recurring billing schedule through the official Upstash QStash SDK."""
import os

from qstash import QStash


def main() -> None:
    token = os.environ["QSTASH_TOKEN"]
    api_url = os.environ["BACKEND_PUBLIC_URL"].rstrip("/")
    cron = os.getenv("BILLING_CRON", "0 2 * * *")
    destination = f"{api_url}/api/v1/billing/qstash"
    client = QStash(token)
    schedule_id = client.schedule.create(destination=destination, cron=cron)
    print({"schedule_id": schedule_id, "destination": destination, "cron": cron})


if __name__ == "__main__":
    main()
