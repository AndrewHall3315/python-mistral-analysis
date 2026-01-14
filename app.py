"""
Flask REST API for Mistral Document Analysis
Wraps the Python Mistral analysis code for deployment on Railway
"""

from flask import Flask, request, jsonify
import os
import sys
import threading
from mistral_api_handler import MistralAPIHandler
from document_processor import DocumentProcessor
from enhanced_document_processor import EnhancedDocumentProcessor

app = Flask(__name__)

# Supabase configuration for async write-back (using REST API directly)
supabase_url = os.environ.get('SUPABASE_URL')
supabase_service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supabase_configured = bool(supabase_url and supabase_service_key)

# Webhook secret for Supabase webhook authentication
webhook_secret = os.environ.get('SUPABASE_WEBHOOK_SECRET', '').strip()

if supabase_configured:
    print(f"[Supabase] Configured with URL: {supabase_url}")
else:
    print("[Supabase] Not configured - async analysis unavailable", file=sys.stderr)

if webhook_secret:
    print("[Webhook] Secret configured for Supabase webhooks")
else:
    print("[Webhook] SUPABASE_WEBHOOK_SECRET not set - webhook endpoints will reject requests", file=sys.stderr)


def supabase_update(table: str, data: dict, match_column: str, match_value: str) -> bool:
    """
    Update a row in Supabase using the REST API directly.
    This avoids dependency conflicts with the supabase-py library.
    """
    import requests
    import json

    if not supabase_configured:
        return False

    try:
        # Supabase REST API endpoint
        url = f"{supabase_url}/rest/v1/{table}?{match_column}=eq.{match_value}"

        headers = {
            "apikey": supabase_service_key,
            "Authorization": f"Bearer {supabase_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        response = requests.patch(url, headers=headers, json=data, timeout=30)

        if response.status_code in [200, 204]:
            return True
        else:
            print(f"[Supabase] Update failed: {response.status_code} - {response.text}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"[Supabase] Request error: {e}", file=sys.stderr)
        return False

# Initialize Mistral API with key from environment
mistral_api_key = os.environ.get('MISTRAL_API_KEY')
if not mistral_api_key:
    print("WARNING: MISTRAL_API_KEY not set in environment", file=sys.stderr)

mistral_api = MistralAPIHandler(api_key=mistral_api_key)
document_processor = DocumentProcessor(mistral_api=mistral_api)
enhanced_document_processor = EnhancedDocumentProcessor(mistral_api=mistral_api, mistral_api_key=mistral_api_key)

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint

    Returns:
        JSON response with service status
    """
    return jsonify({
        "status": "up",
        "service": "mistral-analysis",
        "version": "1.0.0"
    }), 200


@app.route('/analyze', methods=['POST'])
def analyze_document():
    """
    Analyze document content using Mistral AI

    Request JSON:
    {
        "text": "Document content here...",
        "metadata": {
            "file_name": "document.pdf",
            "file_type": "pdf",
            "word_count": 5000
        }
    }

    Response JSON:
    {
        "success": true,
        "analysis": {
            "content_title": "...",
            "content_authors": "...",
            "initial_analysis": "...",
            "detailed_analysis": "...",
            "classification": "...",
            "catalogue_entry": "...",
            "final_analysis": "...",
            "writing_style_analysis": "...",
            "analytical_frameworks": "...",
            "qa_pairs": "...",
            "comparative_analyses": "...",
            "is_hall_document": 0
        }
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400

        if 'text' not in data:
            return jsonify({
                "success": False,
                "error": "No text provided in request body"
            }), 400

        text = data['text']
        metadata = data.get('metadata', {})

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Text content is empty"
            }), 400

        # Log request info
        print(f"[ANALYZE] Processing document: {metadata.get('file_name', 'unknown')}")
        print(f"[ANALYZE] Text length: {len(text)} chars")
        print(f"[ANALYZE] Metadata: {metadata}")

        # Process document using DocumentProcessor
        result = document_processor.process_document(
            content=text,
            metadata=metadata
        )

        # Log success
        print(f"[ANALYZE] Analysis complete for {metadata.get('file_name', 'unknown')}")
        print(f"[ANALYZE] Title: {result.get('content_title', 'N/A')}")
        print(f"[ANALYZE] Authors: {result.get('content_authors', 'N/A')}")

        # Return successful response
        return jsonify({
            "success": True,
            "analysis": result
        }), 200

    except Exception as e:
        # Log error
        print(f"[ERROR] Analysis failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # Return error response
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/analyze-complete', methods=['POST'])
def analyze_document_complete():
    """
    Complete document analysis including vector embeddings and graph data.

    Request JSON:
    {
        "text": "Document content here...",
        "metadata": {
            "file_name": "document.pdf",
            "file_type": "pdf",
            "word_count": 5000
        }
    }

    Response JSON:
    {
        "success": true,
        "analysis": {
            // Standard 11 analysis fields
            "content_title": "...",
            "content_authors": "...",
            "initial_analysis": "...",
            "detailed_analysis": "...",
            "classification": "...",
            "catalogue_entry": "...",
            "final_analysis": "...",
            "writing_style_analysis": "...",
            "analytical_frameworks": "...",
            "qa_pairs": "...",
            "comparative_analyses": "...",
            "is_hall_document": 0,

            // NEW: Vector and graph fields
            "embedding_vector_pg": [...],  // 1024-dimensional vector (Mistral native)
            "embedding_metadata": {...},
            "entities": {...},
            "relationships": [...],
            "graph_metadata": {...}
        }
    }
    """
    try:
        # Get JSON data from request
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400

        if 'text' not in data:
            return jsonify({
                "success": False,
                "error": "No text provided in request body"
            }), 400

        text = data['text']
        metadata = data.get('metadata', {})

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Text content is empty"
            }), 400

        # Log request info
        print(f"[ANALYZE-COMPLETE] Processing document: {metadata.get('file_name', 'unknown')}")
        print(f"[ANALYZE-COMPLETE] Text length: {len(text)} chars")

        # Process document using EnhancedDocumentProcessor
        result = enhanced_document_processor.process_document_complete(
            content=text,
            metadata=metadata
        )

        # Log success
        print(f"[ANALYZE-COMPLETE] Analysis complete for {metadata.get('file_name', 'unknown')}")
        print(f"[ANALYZE-COMPLETE] Title: {result.get('content_title', 'N/A')}")
        print(f"[ANALYZE-COMPLETE] Entities: {sum(len(v) for v in result.get('entities', {}).values())} total")
        print(f"[ANALYZE-COMPLETE] Relationships: {len(result.get('relationships', []))} total")

        # Return successful response
        return jsonify({
            "success": True,
            "analysis": result
        }), 200

    except Exception as e:
        # Log error
        print(f"[ERROR] Complete analysis failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # Return error response
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def run_async_analysis(queue_id: str, text: str, metadata: dict):
    """
    Background thread function to run Mistral analysis and write results to Supabase.
    This allows the HTTP request to return immediately while processing continues.
    """
    try:
        print(f"[ASYNC] Starting background analysis for queue_id: {queue_id}")
        print(f"[ASYNC] File: {metadata.get('file_name', 'unknown')}, Text length: {len(text)} chars")

        # Update status to show analysis started
        supabase_update('processing_queue', {
            'current_step': 'AI analysis in progress...',
            'progress': 30
        }, 'id', queue_id)

        # Run the full analysis
        result = enhanced_document_processor.process_document_complete(
            content=text,
            metadata=metadata
        )

        print(f"[ASYNC] Analysis complete for {metadata.get('file_name', 'unknown')}")
        print(f"[ASYNC] Title: {result.get('content_title', 'N/A')}")

        # Convert content_authors to array if it's a string
        content_authors = result.get('content_authors')
        if content_authors and isinstance(content_authors, str):
            content_authors = [content_authors]

        # Write results to Supabase
        update_data = {
            'current_step': 'analysis_complete',
            'progress': 90,
            # Analysis fields
            'content_title': result.get('content_title'),
            'content_authors': content_authors,
            'initial_analysis': result.get('initial_analysis'),
            'detailed_analysis': result.get('detailed_analysis'),
            'classification': result.get('classification'),
            'catalogue_entry': result.get('catalogue_entry'),
            'final_analysis': result.get('final_analysis'),
            'is_hall_document': result.get('is_hall_document', 0),
            # Vector and graph fields
            'embedding_vector_pg': result.get('embedding_vector_pg'),
            'embedding_metadata': result.get('embedding_metadata'),
            'entities': result.get('entities'),
            'relationships': result.get('relationships'),
            'graph_metadata': result.get('graph_metadata')
        }

        if supabase_update('processing_queue', update_data, 'id', queue_id):
            print(f"[ASYNC] ✅ Results written to Supabase for queue_id: {queue_id}")
        else:
            print(f"[ASYNC] ⚠️ Failed to write results to Supabase!")

    except Exception as e:
        print(f"[ASYNC ERROR] Analysis failed for queue_id {queue_id}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # Update status to show failure
        supabase_update('processing_queue', {
            'current_step': 'analysis_failed',
            'error_message': str(e)
        }, 'id', queue_id)


@app.route('/analyze-async', methods=['POST'])
def analyze_document_async():
    """
    Async document analysis - returns immediately and processes in background.
    Results are written directly to Supabase when complete.

    Request JSON:
    {
        "queue_id": "uuid-of-processing-queue-item",
        "text": "Document content here...",
        "metadata": {
            "file_name": "document.pdf",
            "file_type": "pdf",
            "word_count": 5000
        }
    }

    Response JSON (immediate):
    {
        "success": true,
        "message": "Analysis started",
        "queue_id": "uuid-of-processing-queue-item"
    }

    Results are written to processing_queue table when complete.
    Poll the table for current_step = 'analysis_complete' or 'analysis_failed'
    """
    try:
        # Check Supabase is configured
        if not supabase_configured:
            return jsonify({
                "success": False,
                "error": "Supabase not configured - async analysis unavailable. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars."
            }), 503

        # Get JSON data from request
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400

        if 'queue_id' not in data:
            return jsonify({
                "success": False,
                "error": "No queue_id provided"
            }), 400

        if 'text' not in data:
            return jsonify({
                "success": False,
                "error": "No text provided in request body"
            }), 400

        queue_id = data['queue_id']
        text = data['text']
        metadata = data.get('metadata', {})

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Text content is empty"
            }), 400

        # Log request info
        print(f"[ANALYZE-ASYNC] Received request for queue_id: {queue_id}")
        print(f"[ANALYZE-ASYNC] File: {metadata.get('file_name', 'unknown')}, Text length: {len(text)} chars")

        # Start background thread for processing
        thread = threading.Thread(
            target=run_async_analysis,
            args=(queue_id, text, metadata),
            daemon=True
        )
        thread.start()

        print(f"[ANALYZE-ASYNC] Background thread started for queue_id: {queue_id}")

        # Return immediately
        return jsonify({
            "success": True,
            "message": "Analysis started",
            "queue_id": queue_id
        }), 202  # 202 Accepted

    except Exception as e:
        print(f"[ERROR] Async analysis request failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/test', methods=['POST'])
def test_analysis():
    """
    Test endpoint with minimal analysis (for debugging)

    Request JSON:
    {
        "text": "Sample text here..."
    }

    Returns basic analysis without full pipeline
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "error": "No text provided"
            }), 400

        text = data['text']

        # Basic test - just confirm we can receive and process text
        word_count = len(text.split())
        char_count = len(text)

        return jsonify({
            "success": True,
            "test_result": {
                "received_chars": char_count,
                "word_count": word_count,
                "first_100_chars": text[:100],
                "mistral_api_available": mistral_api_key is not None
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# WEBHOOK HELPER FUNCTIONS
# ============================================================

def verify_webhook_secret(request_obj):
    """
    Verify Supabase webhook authentication via X-Webhook-Secret header.
    Returns (True, None) if valid, (False, error_response) if invalid.
    """
    if not webhook_secret:
        print("[Webhook] SUPABASE_WEBHOOK_SECRET not configured", file=sys.stderr)
        return False, (jsonify({"error": "Webhook secret not configured"}), 500)

    provided_secret = request_obj.headers.get('X-Webhook-Secret', '')
    if provided_secret != webhook_secret:
        print("[Webhook] Invalid webhook secret provided", file=sys.stderr)
        return False, (jsonify({"error": "Unauthorized"}), 401)

    return True, None


def check_idempotency(queue_id: str, expected_status: str) -> bool:
    """
    Check if document is still in expected status.
    Returns False if already processed (skip this webhook).
    """
    import requests

    if not supabase_configured:
        return False

    try:
        url = f"{supabase_url}/rest/v1/processing_queue?id=eq.{queue_id}&select=status"
        headers = {
            'Authorization': f'Bearer {supabase_service_key}',
            'apikey': supabase_service_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"[Idempotency] Failed to fetch status: {response.status_code}", file=sys.stderr)
            return False

        data = response.json()
        if not data or len(data) == 0:
            print(f"[Idempotency] Queue record {queue_id} not found", file=sys.stderr)
            return False

        current_status = data[0].get('status')
        if current_status != expected_status:
            print(f"[Idempotency] {queue_id} is '{current_status}', expected '{expected_status}'. Skipping.")
            return False

        return True

    except Exception as e:
        print(f"[Idempotency] Error checking status: {e}", file=sys.stderr)
        return False


def get_queue_record(queue_id: str) -> dict:
    """
    Fetch full queue record from Supabase.
    """
    import requests

    if not supabase_configured:
        return None

    try:
        url = f"{supabase_url}/rest/v1/processing_queue?id=eq.{queue_id}&select=*"
        headers = {
            'Authorization': f'Bearer {supabase_service_key}',
            'apikey': supabase_service_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        if not data or len(data) == 0:
            return None

        return data[0]

    except Exception as e:
        print(f"[Queue] Error fetching record: {e}", file=sys.stderr)
        return None


# ============================================================
# SUPABASE WEBHOOK ENDPOINT
# ============================================================

@app.route('/webhook/start-analysis', methods=['POST'])
def webhook_start_analysis():
    """
    Supabase webhook endpoint for starting Mistral analysis.
    Triggered on UPDATE to processing_queue when status changes to 'ocr_complete'.

    Supabase webhook payload:
    {
        "type": "UPDATE",
        "table": "processing_queue",
        "schema": "public",
        "record": { ... new record ... },
        "old_record": { ... old record ... }
    }
    """
    # Verify webhook secret
    valid, error_response = verify_webhook_secret(request)
    if not valid:
        return error_response

    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "No payload provided"}), 400

        record = payload.get('record', {})
        old_record = payload.get('old_record', {})
        queue_id = record.get('id')

        if not queue_id:
            return jsonify({"error": "No queue_id in payload"}), 400

        print(f"[Webhook Analysis] Received for queue_id: {queue_id}")

        # Only process if status CHANGED to 'ocr_complete'
        new_status = record.get('status')
        old_status = old_record.get('status') if old_record else None

        if new_status != 'ocr_complete':
            print(f"[Webhook Analysis] Status is '{new_status}', not 'ocr_complete'. Skipping.")
            return jsonify({"status": "skipped", "reason": "status is not ocr_complete"}), 200

        if old_status == 'ocr_complete':
            print(f"[Webhook Analysis] Status unchanged (was already 'ocr_complete'). Skipping.")
            return jsonify({"status": "skipped", "reason": "status unchanged"}), 200

        # Idempotency check
        if not check_idempotency(queue_id, 'ocr_complete'):
            return jsonify({"status": "skipped", "reason": "already processing"}), 200

        # Get content from record or fetch fresh
        content = record.get('content')
        if not content:
            fresh_record = get_queue_record(queue_id)
            if fresh_record:
                content = fresh_record.get('content')
                record = fresh_record  # Use full record

        # Check for empty/minimal content
        if not content or len(content.strip()) < 50:
            print(f"[Webhook Analysis] Empty or minimal content ({len(content) if content else 0} chars). Skipping analysis.")
            # Set to ready without analysis
            from datetime import datetime
            supabase_update('processing_queue', {
                'status': 'ready',
                'current_step': 'Completed (no content to analyze)',
                'progress': 100,
                'completed_at': datetime.utcnow().isoformat()
            }, 'id', queue_id)
            return jsonify({"status": "completed", "reason": "empty content, skipped analysis"}), 200

        # Build metadata
        metadata = {
            'file_name': record.get('file_name', 'document'),
            'file_type': record.get('file_type', 'pdf'),
            'word_count': len(content.split())
        }

        # Start background processing
        thread = threading.Thread(
            target=run_webhook_analysis,
            args=(queue_id, content, metadata),
            daemon=True
        )
        thread.start()

        return jsonify({"status": "accepted", "queue_id": queue_id}), 202

    except Exception as e:
        print(f"[Webhook Analysis] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def run_webhook_analysis(queue_id: str, text: str, metadata: dict):
    """
    Background thread function for webhook-triggered Mistral analysis.
    Runs analysis and sets status to analysis_complete when done.
    """
    from datetime import datetime

    try:
        print(f"[Webhook Analysis] Starting for queue_id: {queue_id}")
        print(f"[Webhook Analysis] File: {metadata.get('file_name', 'unknown')}, Text length: {len(text)} chars")

        # Update status to 'analysis_in_progress'
        supabase_update('processing_queue', {
            'status': 'analysis_in_progress',
            'current_step': 'AI analysis in progress...',
            'progress': 75
        }, 'id', queue_id)

        # Run the full analysis
        result = enhanced_document_processor.process_document_complete(
            content=text,
            metadata=metadata
        )

        print(f"[Webhook Analysis] Analysis complete for {metadata.get('file_name', 'unknown')}")
        print(f"[Webhook Analysis] Title: {result.get('content_title', 'N/A')}")

        # Convert content_authors to array if it's a string
        content_authors = result.get('content_authors')
        if content_authors and isinstance(content_authors, str):
            content_authors = [content_authors]

        # Write results to Supabase with status 'analysis_complete'
        update_data = {
            'status': 'analysis_complete',
            'current_step': 'Analysis complete, extracting fields...',
            'progress': 90,
            # Analysis fields
            'content_title': result.get('content_title'),
            'content_authors': content_authors,
            'initial_analysis': result.get('initial_analysis'),
            'detailed_analysis': result.get('detailed_analysis'),
            'classification': result.get('classification'),
            'catalogue_entry': result.get('catalogue_entry'),
            'final_analysis': result.get('final_analysis'),
            'is_hall_document': result.get('is_hall_document', 0),
            # Vector and graph fields
            'embedding_vector_pg': result.get('embedding_vector_pg'),
            'embedding_metadata': result.get('embedding_metadata'),
            'entities': result.get('entities'),
            'relationships': result.get('relationships'),
            'graph_metadata': result.get('graph_metadata')
        }

        if supabase_update('processing_queue', update_data, 'id', queue_id):
            print(f"[Webhook Analysis] ✅ Results written to Supabase for queue_id: {queue_id}")
        else:
            print(f"[Webhook Analysis] ⚠️ Failed to write results to Supabase!", file=sys.stderr)

    except Exception as e:
        print(f"[Webhook Analysis] Failed for queue_id {queue_id}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()

        # Update status to failed
        supabase_update('processing_queue', {
            'status': 'failed',
            'error_message': str(e),
            'current_step': f'Analysis failed: {str(e)}'
        }, 'id', queue_id)


if __name__ == '__main__':
    # Get port from environment (Railway sets this automatically)
    port = int(os.environ.get('PORT', 8080))

    # Print startup info
    print(f"Starting Mistral Analysis Service on port {port}")
    print(f"Mistral API Key present: {mistral_api_key is not None}")

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
