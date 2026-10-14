FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --chown=10001:10001 brain-runtime /app/brain-runtime
COPY --chown=10001:10001 humanizer-local /app/humanizer-local
COPY --chown=10001:10001 scientific-brains /app/scientific-brains
USER 10001:10001
CMD ["python3","/app/brain-runtime/supervisor.py","--config","/state/person-a.json","--interval","1800"]
