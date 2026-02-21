FROM node:20-alpine
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN if [ -f package.json ]; then npm install; else echo "No package.json yet"; fi
COPY frontend/ .
EXPOSE 3000
CMD ["sh", "-c", "if [ -f package.json ]; then npm run dev -- --host 0.0.0.0 --port 3000; else tail -f /dev/null; fi"]
