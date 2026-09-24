# syntax=docker/dockerfile:1

# 1. Interface React compilée (vite outDir = ../backend/static)
FROM node:24-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Exécution
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FASOSEARCH_MODE=prod FASOSEARCH_HOST=0.0.0.0 FASOSEARCH_PORT=8000
WORKDIR /app
COPY requirements-prod.txt .
# Nettoyage après installation (couches pip volumineuses, cf. .superpowers/sdd rapport
# task-5) : bytecode, répertoires de tests des paquets, et symboles de debug des .so
# (binutils est installé et retiré dans la même couche pour ne rien laisser derrière).
RUN pip install --no-cache-dir -r requirements-prod.txt \
 && find /usr/local/lib/python3.12/site-packages -type d -name '__pycache__' -exec rm -rf {} + \
 && find /usr/local/lib/python3.12/site-packages -type d \( -name 'tests' -o -name 'test' \) -exec rm -rf {} + \
 && apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends binutils \
 && find /usr/local/lib/python3.12/site-packages -name '*.so' -exec strip --strip-unneeded {} + \
 && apt-get purge -y -qq binutils \
 && apt-get autoremove -y -qq \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 app
COPY --chown=app:app backend/ backend/
COPY --chown=app:app scripts/__init__.py scripts/build_index.py scripts/
COPY --chown=app:app run.py ./
# L'empreinte de l'index couvre ces 3 fichiers : ils doivent être présents pour que
# is_stale() soit faux en production (sinon le conteneur refuse de démarrer).
COPY --chown=app:app data/base_complete.xlsx data/w2v_extra.txt data/w2v_cs.txt data/doi.json data/
COPY --chown=app:app models/ models/
COPY --chown=app:app lang_models/ lang_models/
COPY --chown=app:app nltk_data/ nltk_data/
COPY --from=frontend --chown=app:app /src/backend/static backend/static
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
CMD ["python", "run.py"]
