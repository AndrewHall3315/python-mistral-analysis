"""
Enhanced Document Processor with Vector Embeddings and Graph Data
Extends DocumentProcessor to populate:
- embedding_vector_pg
- embedding_metadata
- entities
- relationships
- graph_metadata
- search_vector (auto-populated by PostgreSQL trigger)
"""

import logging
import requests
import json
from typing import Dict, Any, List, Optional
from document_processor import DocumentProcessor
from vector_graph_processor import VectorGraphProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor(DocumentProcessor):
    """
    Extended DocumentProcessor that generates vector embeddings and graph data
    for the processing_queue table.
    """

    def __init__(self, mistral_api, mistral_api_key: str):
        """
        Initialize enhanced document processor.

        Args:
            mistral_api: MistralAPIHandler instance
            mistral_api_key: Mistral API key for embeddings API
        """
        super().__init__(mistral_api)
        self.vector_graph_processor = VectorGraphProcessor(mistral_api)
        self.mistral_api_key = mistral_api_key
        logger.info("EnhancedDocumentProcessor initialized")

    def process_document_complete(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline including:
        1. Standard Mistral analysis (7 fields)
        2. Vector embedding generation
        3. Embedding metadata
        4. Entity extraction
        5. Relationship extraction
        6. Graph metadata
        7. search_vector (auto-populated by PostgreSQL)

        Args:
            content: Document text content
            metadata: Document metadata dict

        Returns:
            dict: Complete analysis result with all fields
            {
                # Standard analysis fields (7)
                "content_title": "...",
                "content_authors": "...",
                "initial_analysis": "...",
                "detailed_analysis": "...",
                "classification": "...",
                "catalogue_entry": "...",
                "final_analysis": "...",
                "is_hall_document": 0,

                # NEW: Vector and graph fields (5)
                "embedding_vector_pg": [...],  # 1024-dimensional vector (Mistral native)
                "embedding_metadata": {...},
                "entities": {...},
                "relationships": [...],
                "graph_metadata": {...}

                # search_vector is auto-populated by PostgreSQL trigger
            }
        """
        logger.info(f"[Enhanced] Processing document: {metadata.get('file_name', 'unknown')}")

        # Step 1: Run standard document analysis
        logger.info("[Enhanced] Step 1: Running standard Mistral analysis...")
        analysis_result = self.process_document(content, metadata)

        # Step 2: Generate vector embedding
        logger.info("[Enhanced] Step 2: Generating vector embedding...")
        embedding_text = self._prepare_embedding_text(
            title=analysis_result.get('content_title', ''),
            description=analysis_result.get('catalogue_entry', '')[:500],
            initial_analysis=analysis_result.get('initial_analysis', ''),
            detailed_analysis=analysis_result.get('detailed_analysis', '')
        )

        embedding_vector = self._generate_mistral_embedding(embedding_text)

        # Step 3: Create embedding metadata
        logger.info("[Enhanced] Step 3: Creating embedding metadata...")
        embedding_metadata = self.vector_graph_processor.create_embedding_metadata(
            embedding_vector
        )

        # Step 4: Extract entities
        logger.info("[Enhanced] Step 4: Extracting entities...")
        entities = self.vector_graph_processor.extract_entities(
            initial_analysis=analysis_result.get('initial_analysis', ''),
            detailed_analysis=analysis_result.get('detailed_analysis', ''),
            catalogue_entry=analysis_result.get('catalogue_entry', ''),
            qa_pairs=''  # No longer generating QA pairs for fine-tuning
        )

        # Step 5: Extract relationships
        logger.info("[Enhanced] Step 5: Extracting relationships...")
        relationships = self.vector_graph_processor.extract_relationships(
            entities=entities,
            initial_analysis=analysis_result.get('initial_analysis', ''),
            detailed_analysis=analysis_result.get('detailed_analysis', ''),
            catalogue_entry=analysis_result.get('catalogue_entry', '')
        )

        # Step 6: Create graph metadata
        logger.info("[Enhanced] Step 6: Creating graph metadata...")
        graph_metadata = self.vector_graph_processor.create_graph_metadata(
            entities=entities,
            relationships=relationships
        )

        # Step 7: Combine all results
        complete_result = {
            **analysis_result,  # Include all 11 standard fields
            "embedding_vector_pg": embedding_vector,
            "embedding_metadata": embedding_metadata,
            "entities": entities,
            "relationships": relationships,
            "graph_metadata": graph_metadata
        }

        logger.info("[Enhanced] ✅ Complete processing finished")
        logger.info(f"[Enhanced] Generated {len(embedding_vector)} embedding dimensions")
        logger.info(f"[Enhanced] Extracted {sum(len(v) for v in entities.values())} entities")
        logger.info(f"[Enhanced] Extracted {len(relationships)} relationships")

        return complete_result

    def _prepare_embedding_text(
        self,
        title: str,
        description: str,
        initial_analysis: str,
        detailed_analysis: str
    ) -> str:
        """
        Prepare text for embedding generation.
        Combines key document information with reasonable length.

        Args:
            title: Document title
            description: Short description
            initial_analysis: Initial analysis
            detailed_analysis: Detailed analysis

        Returns:
            str: Combined text for embedding (max ~4000 chars)
        """
        # Build embedding text with priority weighting
        parts = [
            f"Title: {title}",
            f"\nDescription: {description[:500]}",
            f"\nInitial Analysis: {initial_analysis[:1000]}",
            f"\nDetailed Analysis: {detailed_analysis[:2000]}"
        ]

        embedding_text = '\n'.join(parts)

        # Truncate if too long (Mistral embed has ~8K token limit, roughly 32K chars)
        if len(embedding_text) > 25000:
            embedding_text = embedding_text[:25000]

        logger.info(f"Prepared embedding text: {len(embedding_text)} chars")
        return embedding_text

    def _generate_mistral_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding using Mistral embeddings API.

        Args:
            text: Text to embed

        Returns:
            list: 1024-dimensional embedding vector (Mistral's native output)

        Note: This uses the Mistral embeddings endpoint, NOT the chat endpoint
        Note: Mistral embed model returns 1024 dimensions natively
        """
        logger.info(f"Generating Mistral embedding for {len(text)} chars of text...")

        try:
            # Mistral embeddings API endpoint
            url = "https://api.mistral.ai/v1/embeddings"

            # Request headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.mistral_api_key}"
            }

            # Request body
            data = {
                "model": "mistral-embed",
                "input": [text]  # Mistral expects array of strings
            }

            # Make API call
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=60
            )

            # Check response
            if response.status_code == 200:
                result = response.json()
                embedding = result['data'][0]['embedding']
                logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
                return embedding
            else:
                logger.error(f"Mistral embeddings API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                # Return zero vector as fallback (1024 dimensions)
                return [0.0] * 1024

        except requests.exceptions.Timeout:
            logger.error("Mistral embeddings API timeout")
            return [0.0] * 1024

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            import traceback
            traceback.print_exc()
            return [0.0] * 1024


# Standalone function for use in existing code
def process_document_with_vectors(
    content: str,
    metadata: Dict[str, Any],
    mistral_api,
    mistral_api_key: str
) -> Dict[str, Any]:
    """
    Convenience function to process a document with full vector/graph extraction.

    Args:
        content: Document text content
        metadata: Document metadata
        mistral_api: MistralAPIHandler instance
        mistral_api_key: Mistral API key string

    Returns:
        dict: Complete processing result
    """
    processor = EnhancedDocumentProcessor(mistral_api, mistral_api_key)
    return processor.process_document_complete(content, metadata)


if __name__ == "__main__":
    # Test code
    print("Testing EnhancedDocumentProcessor...")

    # This requires actual API keys to test
    # Example usage:
    # from mistral_api_handler import MistralAPIHandler
    #
    # api_key = "your-mistral-api-key"
    # mistral_api = MistralAPIHandler(api_key)
    # processor = EnhancedDocumentProcessor(mistral_api, api_key)
    #
    # result = processor.process_document_complete(
    #     content="Document text...",
    #     metadata={"file_name": "test.pdf", "file_type": "pdf"}
    # )
    #
    # print(json.dumps(result, indent=2))

    print("✅ Module loaded successfully")
    print("Note: Actual testing requires Mistral API key")
