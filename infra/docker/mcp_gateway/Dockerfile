FROM python:3.11-slim
WORKDIR /app
COPY mcp_gateway/ /app/mcp_gateway/
EXPOSE 6100
CMD ["python", "-m", "mcp_gateway.app.main"]
