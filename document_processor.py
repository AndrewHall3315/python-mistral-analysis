"""
Simplified Document Processor for Railway Deployment
Processes document content and returns Mistral analysis results
"""

import logging
from typing import Dict, Any
from mistral_api_handler import MistralAPIHandler
from urban_planning_analysis import UrbanPlanningAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes document content using Mistral AI analysis
    Simplified version for stateless REST API deployment
    """

    def __init__(self, mistral_api: MistralAPIHandler):
        """
        Initialize document processor

        Args:
            mistral_api: MistralAPIHandler instance with API credentials
        """
        self.mistral_api = mistral_api
        self.urban_analyzer = UrbanPlanningAnalysis(mistral_api=mistral_api)

    def process_document(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document content and return analysis.

        Args:
            content: Document text content
            metadata: Dict with file_name, file_type, word_count, etc.

        Returns:
            Dict with all 7 analysis fields:
            - content_title
            - content_authors
            - initial_analysis
            - detailed_analysis
            - classification
            - catalogue_entry
            - final_analysis
            - is_hall_document
        """
        logger.info(f"[DocumentProcessor] Processing: {metadata.get('file_name', 'unknown')}")
        logger.info(f"[DocumentProcessor] Content length: {len(content)} chars")

        # Prepare content_analysis dict from metadata for compatibility
        content_analysis = {
            'File name': metadata.get('file_name', 'Unknown'),
            'File type': metadata.get('file_type', 'Unknown'),
            'word_count': metadata.get('word_count', len(content.split())),
            'possible_authors': metadata.get('possible_authors', []),
            'possible_dates': [],
            'Author': metadata.get('Author', metadata.get('author', 'Unknown')),
            'Creation Date': metadata.get('Creation Date', 'Unknown'),
            'created': metadata.get('created'),
            'Title': metadata.get('title', metadata.get('file_name', 'Unknown'))
        }

        try:
            # Run urban planning analysis (this generates most fields)
            analysis_result = self.urban_analyzer.analyze_document(content, content_analysis)

            # Check if analysis failed
            if 'error' in analysis_result:
                logger.error(f"[DocumentProcessor] Analysis failed: {analysis_result['error']}")
                return {
                    'content_title': 'Analysis Failed',
                    'content_authors': 'Unknown',
                    'initial_analysis': analysis_result.get('fallback_analysis', 'Analysis failed'),
                    'detailed_analysis': '',
                    'classification': '',
                    'catalogue_entry': '',
                    'final_analysis': analysis_result.get('error', 'Analysis failed'),
                    'is_hall_document': 0
                }

            logger.info(f"[DocumentProcessor] Urban analysis complete")
            logger.info(f"[DocumentProcessor] Title: {analysis_result.get('content_title', 'N/A')}")
            logger.info(f"[DocumentProcessor] Final analysis included from urban_analyzer")

            # Return all 8 fields (final_analysis now comes from urban_analyzer)
            return {
                'content_title': analysis_result.get('content_title', ''),
                'content_authors': analysis_result.get('content_authors', ''),
                'initial_analysis': analysis_result.get('initial_analysis', ''),
                'detailed_analysis': analysis_result.get('detailed_analysis', ''),
                'classification': analysis_result.get('classification', ''),
                'catalogue_entry': analysis_result.get('catalogue_entry', ''),
                'final_analysis': analysis_result.get('final_analysis', ''),
                'is_hall_document': analysis_result.get('is_hall_document', 0)
            }

        except Exception as e:
            logger.error(f"[DocumentProcessor] ERROR processing document: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                'content_title': 'Processing Error',
                'content_authors': 'Unknown',
                'initial_analysis': f"Error: {str(e)}",
                'detailed_analysis': '',
                'classification': '',
                'catalogue_entry': '',
                'final_analysis': f"Document processing failed: {str(e)}",
                'is_hall_document': 0
            }
