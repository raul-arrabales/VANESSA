FROM python:3.11-slim
WORKDIR /app
COPY mcp_gateway/ /app/mcp_gateway/
EXPOSE 8080
CMD ["python", "-m", "mcp_gateway.app.main"]
