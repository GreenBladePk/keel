FROM python:3.12-slim
WORKDIR /app
COPY . .
# [llm] pulls litellm + instructor so the Gemini/Vertex judge works in prod
RUN pip install --no-cache-dir ".[llm]"
# Cloud Run sets $PORT (default 8080); keel.server reads it and binds 0.0.0.0
ENV PORT=8080
EXPOSE 8080
CMD ["python", "-m", "keel.server"]
