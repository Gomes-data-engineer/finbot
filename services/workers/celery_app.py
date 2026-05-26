import os
from celery import Celery

# Configuração da URL do Redis (padrão local docker e fallback localhost)
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "finbot_workers",
    broker=redis_url,
    backend=redis_url,
    include=["tasks"]
)

# Configurações do Celery para conformidade de formatos
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
)

if __name__ == "__main__":
    app.start()
