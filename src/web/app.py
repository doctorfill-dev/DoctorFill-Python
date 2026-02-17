"""
Flask Web Application for DoctorFill.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import List

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from ..config.settings import (
    API_HOST,
    API_PORT,
    DEBUG,
    MAX_UPLOAD_BYTES,
    LOG_PDF_DIR,
)
from ..config import user_config
from ..core.template_manager import TemplateManager
from ..pipeline.orchestrator import PipelineOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="")

# Enable CORS for Tauri webview (tauri://localhost) and local dev
CORS(app, origins=["tauri://localhost", "http://localhost:*", "https://tauri.localhost"])

# Configure upload limits
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

# Initialize components
template_manager = TemplateManager()


@app.route("/")
def index():
    """Serve the main page."""
    return app.send_static_file("index.html")


@app.route("/forms", methods=["GET"])
def list_forms():
    """List available forms."""
    try:
        forms = template_manager.list_forms()
        return jsonify(forms)
    except Exception as e:
        logger.error("Error listing forms: %s", e)
        return jsonify({"error": str(e)}), 500


# Allowed file extensions for reports
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def _is_allowed_file(filename: str) -> bool:
    """Check if file has allowed extension."""
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)


def _get_extension(filename: str) -> str:
    """Get file extension."""
    return Path(filename).suffix.lower()


@app.route("/fill/<form_id>", methods=["POST"])
def fill_form(form_id: str):
    """
    Fill a form with data from uploaded reports.

    Expects multipart/form-data with 'reports' field containing PDF or TXT files.
    """
    try:
        # Validate form exists
        descriptor = template_manager.get_descriptor(form_id)

        # Get uploaded files
        if "reports" not in request.files:
            return jsonify({"error": "No reports uploaded"}), 400

        files = request.files.getlist("reports")
        if not files:
            return jsonify({"error": "No reports uploaded"}), 400

        # Validate files have allowed extensions
        for f in files:
            if not _is_allowed_file(f.filename):
                return jsonify({
                    "error": f"Invalid file: {f.filename}. Allowed formats: PDF, TXT"
                }), 400

        # Save uploaded files to temp directory
        temp_dir = Path(tempfile.mkdtemp())
        report_paths: List[Path] = []

        try:
            for f in files:
                # Use UUID + original extension to prevent path traversal
                ext = _get_extension(f.filename)
                safe_name = f"{uuid.uuid4().hex}{ext}"
                temp_path = temp_dir / safe_name
                f.save(temp_path)
                report_paths.append(temp_path)

            # Process the form
            logger.info("Processing form %s with %d reports", form_id, len(report_paths))

            orchestrator = PipelineOrchestrator(template_manager=template_manager)
            result = orchestrator.process(
                form_id=form_id,
                report_pdfs=report_paths,
                save_logs=True
            )

            if not result.success:
                return jsonify({"error": result.error or "Processing failed"}), 500

            if not result.output_pdf or not result.output_pdf.exists():
                return jsonify({"error": "Output PDF not generated"}), 500

            # Send the filled PDF
            return send_file(
                result.output_pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{descriptor.name}_filled.pdf"
            )

        finally:
            # Clean up temp files
            for p in report_paths:
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                temp_dir.rmdir()
            except Exception:
                pass

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Error filling form: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


# ──────────────────────────────────────────────────────────────
# Configuration endpoints
# ──────────────────────────────────────────────────────────────

@app.route("/config", methods=["GET"])
def get_config():
    """Get current user configuration (keys are masked)."""
    cfg = user_config.load()
    # Mask sensitive values for the frontend
    masked = dict(cfg)
    token = masked.get("ifk_api_token", "")
    if token and len(token) > 8:
        masked["ifk_api_token"] = token[:4] + "****" + token[-4:]
    elif token:
        masked["ifk_api_token"] = "****"
    return jsonify({
        "configured": user_config.is_configured(),
        "config": masked,
    })


@app.route("/config", methods=["POST"])
def save_config():
    """Save user configuration."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    cfg = user_config.load()

    # Only update allowed keys
    allowed_keys = {"llm_provider", "ifk_product_id", "ifk_api_token", "lmstudio_base_url"}
    for key in allowed_keys:
        if key in data:
            cfg[key] = data[key].strip()

    user_config.save(cfg)
    return jsonify({"ok": True, "configured": user_config.is_configured()})


@app.route("/config/test", methods=["POST"])
def test_config():
    """Test the current provider connection using saved user config."""
    try:
        cfg = user_config.load()
        provider_type = cfg.get("llm_provider", "infomaniak")

        if provider_type == "infomaniak":
            import requests as req
            product_id = cfg.get("ifk_product_id", "")
            token = cfg.get("ifk_api_token", "")
            if not product_id or not token:
                return jsonify({"ok": False, "error": "Product ID ou API Token manquant"})
            url = f"https://api.infomaniak.com/2/ai/{product_id}/openai/v1/models"
            resp = req.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=5)
            return jsonify({"ok": resp.status_code == 200})
        elif provider_type == "local":
            import requests as req
            base_url = cfg.get("lmstudio_base_url", "")
            if not base_url:
                return jsonify({"ok": False, "error": "URL LM Studio manquante"})
            resp = req.get(f"{base_url}/models", timeout=5)
            return jsonify({"ok": resp.status_code == 200})
        else:
            return jsonify({"ok": False, "error": f"Fournisseur inconnu: {provider_type}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


def main():
    """Run the application."""
    logger.info("Starting DoctorFill on %s:%d", API_HOST, API_PORT)
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
