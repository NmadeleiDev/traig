from celery import Celery

app = Celery("tasks", broker="redis://redis:6379/0", include=["tasks.tasks"])

if __name__ == "__main__":
    app.start()
