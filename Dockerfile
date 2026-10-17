FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY sim sim
COPY servers servers
COPY agent agent
COPY evals evals
RUN pip install --no-cache-dir .
ENV HOST=0.0.0.0 PORT=8000 TRIAGE_DB=/data/prod.db
EXPOSE 8000
CMD ["sh", "-c", "python -m sim.generate --scenario ${SCENARIO:-bad_deploy} && python -m servers.gateway"]