#!/usr/bin/env python3
"""Lightweight webhook receiver for JobTread job-creation events.

Listens for POST /webhook from JobTread, extracts the job ID, and
dispatches process_submission() in a background thread so JobTread
does not time out waiting for a response.
"""

import http.server
import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone

# Load .env before importing anything that needs GRANT_KEY
_DOTENV_PATH = "/home/hermes/developer/JobTread API/.env"


def _load_dotenv(path):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except FileNotFoundError:
        logging.warning("No .env file found at %s", path)


_load_dotenv(_DOTENV_PATH)

sys.path.insert(0, "/home/hermes/developer/JobTread API")
from water_treatment_automator import WaterTreatmentAutomator  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("webhook_server")


def _extract_job_id(payload: dict):
    """Try payload['id'], payload['jobId'], payload['job']['id'] in order."""
    if "id" in payload:
        log.info("Job ID source: payload['id'] = %s", payload["id"])
        return str(payload["id"])
    if "jobId" in payload:
        log.info("Job ID source: payload['jobId'] = %s", payload["jobId"])
        return str(payload["jobId"])
    if "jobID" in payload:
        log.info("Job ID source: payload['jobID'] = %s", payload["jobID"])
        return str(payload["jobID"])
    try:
        jid = payload["job"]["id"]
        log.info("Job ID source: payload['job']['id'] = %s", jid)
        return str(jid)
    except (KeyError, TypeError):
        pass
    return None


def _run_automator(job_id: str):
    try:
        log.info("Background thread: starting process_submission(%s)", job_id)
        automator = WaterTreatmentAutomator()
        result = automator.process_submission(job_id)
        log.info("Background thread: process_submission(%s) complete — %s", job_id, result)
    except Exception:
        log.exception("Background thread: process_submission(%s) raised an exception", job_id)


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info("HTTP %s %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook":
            self._send_json(404, {"error": "not found"})
            return

        expected_secret = os.environ.get("WEBHOOK_SECRET")
        if expected_secret and self.headers.get("X-Webhook-Secret") != expected_secret:
            log.warning("Rejected webhook request: invalid or missing X-Webhook-Secret from %s", self.client_address[0])
            self._send_json(401, {"error": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""

        ts = datetime.now(timezone.utc).isoformat()
        log.info("[%s] POST /webhook — %d bytes from %s", ts, length, self.client_address[0])

        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            log.error("Invalid JSON payload: %s", exc)
            self._send_json(400, {"error": "invalid JSON"})
            return

        # Log a compact payload summary (truncate large payloads)
        summary = json.dumps(payload)
        if len(summary) > 400:
            summary = summary[:400] + "…"
        log.info("Payload summary: %s", summary)

        job_id = _extract_job_id(payload)
        if not job_id:
            log.error("Could not extract job ID from payload keys: %s", list(payload.keys()))
            self._send_json(422, {"error": "job ID not found in payload"})
            return

        # Acknowledge immediately so JobTread does not time out
        self._send_json(200, {"status": "accepted", "jobId": job_id})

        thread = threading.Thread(target=_run_automator, args=(job_id,), daemon=True)
        thread.start()
        log.info("Dispatched background thread for job %s", job_id)


def main():
    port = int(os.environ.get("PORT", 8080))
    server = http.server.HTTPServer(("0.0.0.0", port), WebhookHandler)
    log.info("JobTread webhook server listening on 0.0.0.0:%d", port)
    log.info("Endpoints: POST /webhook, GET /health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
