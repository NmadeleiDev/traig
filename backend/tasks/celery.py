from celery import Celery

redis_url = "redis://redis:6379/0"

app = Celery("tasks", broker=redis_url, include=["tasks.tasks"])
app.conf.result_backend = redis_url

if __name__ == "__main__":
    app.start()
