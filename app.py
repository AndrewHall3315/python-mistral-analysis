"""
Flask REST API for Mistral Document Analysis
Wraps the Python Mistral analysis code for deployment on Railway
"""

from flask import Flask, request, jsonify
import os
import sys
from mistral_api_handler import MistralAPIHandler
from document_processor import DocumentProcessor
from enhanced_document_processor import EnhancedDocumentProcessor

app = Flask(__name__)

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
            "embedding_vector_pg": [...],  // 1536-dimensional vector
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


if __name__ == '__main__':
    # Get port from environment (Railway sets this automatically)
    port = int(os.environ.get('PORT', 8080))

    # Print startup info
    print(f"Starting Mistral Analysis Service on port {port}")
    print(f"Mistral API Key present: {mistral_api_key is not None}")

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
