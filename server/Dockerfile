FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_MODEL_PATH=/app/models/best.pt \
    PLATE_SOLVE_INDEX_DIR=/usr/share/astrometry

WORKDIR /app

# solve-field runs directly inside Linux. Runtime libraries cover OpenCV,
# Astrometry.net and common scientific Python wheels.
RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
        astrometry.net \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /tmp/server-requirements.txt
COPY Constellation/requirements.txt /tmp/constellation-requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.13,<2.14" \
        "torchvision>=0.28,<0.29" \
    && python -m pip install \
        -r /tmp/server-requirements.txt \
        -r /tmp/constellation-requirements.txt

COPY server /app/server
COPY Constellation/scripts /app/Constellation/scripts
COPY Constellation/data/reference /app/Constellation/data/reference
COPY Constellation/HYG-Database-main/hyg/CURRENT/hygdata_v41.csv \
    /app/Constellation/HYG-Database-main/hyg/CURRENT/hygdata_v41.csv

RUN mkdir -p \
    /app/models \
    /app/Constellation/data/results/realtime_plate_solving

WORKDIR /app/server

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

# One worker avoids loading a separate PyTorch model into memory per process.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
