# Live demo API (python -m scripts.serve): reads a description with GigaChat and scores it
# with the saved E2 model. Needs only the code, the configs and artifacts/live. No data.
#
#   docker build -t credit-risk-live .
#   docker run -p 8000:8000 -e GIGACHAT_AUTH_KEY=... credit-risk-live
FROM python:3.12-slim

# curl: to fetch the root certificate below. libgomp1: CatBoost's OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Sber's endpoints are signed by the Russian Trusted Root CA, which is not in the default
# trust store. It is fetched from the official portal over normally verified TLS, and the
# build fails if the file is not a certificate.
RUN mkdir -p /certs \
    && curl -fsSL https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt \
       -o /certs/russian_trusted_root_ca.pem \
    && grep -q "BEGIN CERTIFICATE" /certs/russian_trusted_root_ca.pem
ENV GIGACHAT_CA_BUNDLE=/certs/russian_trusted_root_ca.pem

WORKDIR /app
COPY requirements-live.txt .
RUN pip install --no-cache-dir -r requirements-live.txt

COPY configs configs
COPY src src
COPY scripts scripts
COPY artifacts/live artifacts/live

# The platform's proxy sits in front, so rate limits use the forwarded visitor address.
ENV HOST=0.0.0.0 PORT=8000 LIVE_TRUST_PROXY=true PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "scripts.serve"]
