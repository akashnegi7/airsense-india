FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Build the database at image build time: try live data, fall back to demo data.
RUN python -m airsense.etl.pipeline || python -m airsense.etl.pipeline --demo
ENV PORT=8050
EXPOSE 8050
CMD gunicorn -w 2 -b 0.0.0.0:${PORT} airsense.dashboard.app:server
