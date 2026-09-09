# Serves the public, no-storage demo on Hugging Face Spaces (sdk: docker).
#
# This installs the `demo` extra only -- no SQLAlchemy, no NiceGUI -- so the image
# a Space actually runs has no dependency capable of persisting anything, on top
# of demo/ never importing personality_questionnaire.db (see
# tests/demo/test_isolation.py). CPU-only: nothing here needs a GPU.

FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY personality_questionnaire ./personality_questionnaire
COPY demo ./demo

RUN pip install --no-cache-dir ".[demo]"

# Spaces expect the app on 7860 and probe it unauthenticated. demo.app's own
# CLI default is loopback (right for a local trial run of `pq demo`), so the
# container binding is set explicitly here rather than relying on env vars --
# main() always passes an explicit host/port, which would shadow them anyway.
EXPOSE 7860

CMD ["python", "-m", "demo.app", "--host", "0.0.0.0", "--port", "7860"]
