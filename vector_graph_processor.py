"""
Vector Embeddings and Graph Data Processor for processing_queue
Handles:
1. Vector embedding generation with metadata
2. Entity extraction from document analysis
3. Relationship extraction between entities
4. Graph metadata generation
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorGraphProcessor:
    """
    Processes documents to extract vector embeddings and graph data
    for the processing_queue table.
    """

    def __init__(self, mistral_api):
        """
        Initialize the processor with Mistral API handler.

        Args:
            mistral_api: Instance of MistralAPIHandler
        """
        self.mistral_api = mistral_api
        logger.info("VectorGraphProcessor initialized")

    def create_embedding_metadata(self, embedding_vector: List[float]) -> Dict[str, Any]:
        """
        Create metadata about the embedding vector.

        Args:
            embedding_vector: The 1536-dimensional embedding (padded from Mistral's 1024)

        Returns:
            dict: Metadata in format:
            {
                "model": "mistral-embed",
                "dimensions": 1536,
                "original_dimensions": 1024,
                "created_at": "2025-01-13T10:30:00Z",
                "api_version": "v1",
                "padded": true
            }
        """
        logger.info("Creating embedding metadata")

        try:
            actual_dims = len(embedding_vector) if embedding_vector else 1536

            metadata = {
                "model": "mistral-embed",
                "dimensions": actual_dims,
                "original_dimensions": 1024,  # Mistral embed returns 1024
                "padded": True if actual_dims == 1536 else False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "api_version": "v1"
            }

            logger.info(f"Embedding metadata created: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Error creating embedding metadata: {e}")
            return {
                "model": "mistral-embed",
                "dimensions": 1536,
                "original_dimensions": 1024,
                "padded": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "api_version": "v1",
                "error": str(e)
            }

    def extract_entities(
        self,
        initial_analysis: str,
        detailed_analysis: str,
        catalogue_entry: str,
        qa_pairs: str = ""
    ) -> Dict[str, List[str]]:
        """
        Extract entities from document analysis fields using Mistral AI.

        Categories:
        - cities_places: London, Docklands, Canary Wharf, etc.
        - transport_planning: DLR, railway, transit systems, etc.
        - urban_concepts: regeneration, TOD, sustainability, etc.
        - geographic_spatial: regions, neighborhoods, zones, etc.
        - problems_challenges: congestion, sprawl, etc.
        - solutions_methods: planning policies, interventions, etc.

        Args:
            initial_analysis: Initial document analysis
            detailed_analysis: Detailed document analysis
            catalogue_entry: Catalogue entry text
            qa_pairs: Q&A pairs (optional)

        Returns:
            dict: Entities by category
        """
        logger.info("Extracting entities from document analysis")

        # Combine all analysis text
        combined_text = f"""
        Initial Analysis:
        {initial_analysis[:1000]}

        Detailed Analysis:
        {detailed_analysis[:2000]}

        Catalogue Entry:
        {catalogue_entry[:1000]}
        """

        # Create prompt for entity extraction
        prompt = f"""
        Extract entities from this urban planning document analysis. Categorize them as follows:

        **Categories:**
        1. cities_places: Cities, neighborhoods, landmarks, specific locations
        2. transport_planning: Transportation systems, infrastructure, modes (DLR, railways, bus, etc.)
        3. urban_concepts: Urban planning concepts (regeneration, TOD, sustainability, zoning, etc.)
        4. geographic_spatial: Geographic regions, zones, spatial patterns
        5. problems_challenges: Urban problems, challenges, issues discussed
        6. solutions_methods: Planning solutions, methods, interventions, policies

        **Instructions:**
        - Extract 5-15 entities per category (if present)
        - Use specific names/terms from the text
        - Avoid generic terms unless they're key concepts
        - Include abbreviations if used (e.g., "DLR", "TOD")

        **Format your response EXACTLY as:**

        ENTITIES
        ========

        cities_places:
        - [Entity 1]
        - [Entity 2]
        ...

        transport_planning:
        - [Entity 1]
        - [Entity 2]
        ...

        urban_concepts:
        - [Entity 1]
        - [Entity 2]
        ...

        geographic_spatial:
        - [Entity 1]
        - [Entity 2]
        ...

        problems_challenges:
        - [Entity 1]
        - [Entity 2]
        ...

        solutions_methods:
        - [Entity 1]
        - [Entity 2]
        ...

        **Text to analyze:**
        {combined_text}
        """

        try:
            # Call Mistral API
            response = self.mistral_api.run_command(prompt, max_tokens=800, temperature=0.2)

            # Parse response to extract entities
            entities = self._parse_entity_response(response)

            logger.info(f"Extracted entities: {sum(len(v) for v in entities.values())} total")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            # Return fallback empty structure
            return {
                "cities_places": [],
                "transport_planning": [],
                "urban_concepts": [],
                "geographic_spatial": [],
                "problems_challenges": [],
                "solutions_methods": []
            }

    def _parse_entity_response(self, response: str) -> Dict[str, List[str]]:
        """
        Parse Mistral API response to extract entities by category.

        Args:
            response: Raw response from Mistral API

        Returns:
            dict: Parsed entities by category
        """
        entities = {
            "cities_places": [],
            "transport_planning": [],
            "urban_concepts": [],
            "geographic_spatial": [],
            "problems_challenges": [],
            "solutions_methods": []
        }

        current_category = None
        lines = response.split('\n')

        for line in lines:
            line = line.strip()

            # Check if line is a category header
            if line.endswith(':') and line[:-1] in entities:
                current_category = line[:-1]
                continue

            # Extract entity from bullet point
            if line.startswith('- ') and current_category:
                entity = line[2:].strip()
                if entity and entity not in entities[current_category]:
                    entities[current_category].append(entity)

        return entities

    def extract_relationships(
        self,
        entities: Dict[str, List[str]],
        initial_analysis: str,
        detailed_analysis: str,
        catalogue_entry: str
    ) -> List[Dict[str, str]]:
        """
        Extract relationships between entities using Mistral AI.

        Relationship types:
        - created, located_at, followed, demonstrates, implements
        - compared_to, affects, planned_by, funded_by, connected_to

        Args:
            entities: Extracted entities by category
            initial_analysis: Initial document analysis
            detailed_analysis: Detailed document analysis
            catalogue_entry: Catalogue entry text

        Returns:
            list: Array of relationships
            [
                {"from": "Peter Hall", "relation": "created", "to": "DLR planning study"},
                {"from": "DLR", "relation": "located_at", "to": "Docklands"},
                ...
            ]
        """
        logger.info("Extracting relationships between entities")

        # Flatten entities for the prompt
        all_entities = []
        for category, entity_list in entities.items():
            all_entities.extend(entity_list[:10])  # Limit to top 10 per category

        if not all_entities:
            logger.warning("No entities found - skipping relationship extraction")
            return []

        # Combine analysis text
        combined_text = f"""
        Initial Analysis:
        {initial_analysis[:800]}

        Detailed Analysis:
        {detailed_analysis[:1500]}
        """

        # Create prompt for relationship extraction
        prompt = f"""
        Extract relationships between entities in this urban planning document.

        **Available Entities:**
        {', '.join(all_entities[:30])}

        **Relationship Types:**
        - created: Who created/authored what
        - located_at: What is located where
        - followed: Sequential/temporal relationships
        - demonstrates: Exemplifies a concept
        - implements: Puts into practice
        - compared_to: Comparisons between entities
        - affects: Causal relationships
        - planned_by: Planning/design relationships
        - funded_by: Financial relationships
        - connected_to: Physical/logical connections

        **Instructions:**
        - Extract 5-15 relationships (if present)
        - Use entities from the provided list
        - Base relationships on actual content, not assumptions
        - Be specific and accurate

        **Format your response EXACTLY as:**

        RELATIONSHIPS
        ============

        1. FROM: [Entity 1] | RELATION: [Relationship Type] | TO: [Entity 2]
        2. FROM: [Entity 1] | RELATION: [Relationship Type] | TO: [Entity 2]
        ...

        **Text to analyze:**
        {combined_text}
        """

        try:
            # Call Mistral API
            response = self.mistral_api.run_command(prompt, max_tokens=600, temperature=0.2)

            # Parse response to extract relationships
            relationships = self._parse_relationship_response(response)

            logger.info(f"Extracted {len(relationships)} relationships")
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    def _parse_relationship_response(self, response: str) -> List[Dict[str, str]]:
        """
        Parse Mistral API response to extract relationships.

        Args:
            response: Raw response from Mistral API

        Returns:
            list: Parsed relationships
        """
        relationships = []
        lines = response.split('\n')

        # Pattern: "FROM: X | RELATION: Y | TO: Z"
        pattern = r'FROM:\s*(.+?)\s*\|\s*RELATION:\s*(.+?)\s*\|\s*TO:\s*(.+?)(?:\s*$|\s*\|)'

        for line in lines:
            line = line.strip()

            # Try to match the pattern
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                from_entity = match.group(1).strip()
                relation = match.group(2).strip()
                to_entity = match.group(3).strip()

                relationship = {
                    "from": from_entity,
                    "relation": relation,
                    "to": to_entity
                }

                # Avoid duplicates
                if relationship not in relationships:
                    relationships.append(relationship)

        return relationships

    def create_graph_metadata(
        self,
        entities: Dict[str, List[str]],
        relationships: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Calculate metadata about the extracted graph.

        Args:
            entities: Extracted entities by category
            relationships: Extracted relationships

        Returns:
            dict: Graph statistics
            {
                "total_entities": 25,
                "total_relationships": 12,
                "entity_types": ["cities_places", "transport_planning", ...],
                "extraction_date": "2025-01-13T10:30:00Z",
                "domain": "urban_planning",
                "extraction_method": "mistral_api_llm"
            }
        """
        logger.info("Creating graph metadata")

        try:
            # Count total entities
            total_entities = sum(len(entity_list) for entity_list in entities.values())

            # Get entity types that have entities
            entity_types = [
                category for category, entity_list in entities.items()
                if len(entity_list) > 0
            ]

            # Create metadata
            metadata = {
                "total_entities": total_entities,
                "total_relationships": len(relationships),
                "entity_types": entity_types,
                "entity_counts_by_type": {
                    category: len(entity_list)
                    for category, entity_list in entities.items()
                },
                "extraction_date": datetime.now(timezone.utc).isoformat(),
                "domain": "urban_planning",
                "extraction_method": "mistral_api_llm"
            }

            logger.info(f"Graph metadata created: {total_entities} entities, {len(relationships)} relationships")
            return metadata

        except Exception as e:
            logger.error(f"Error creating graph metadata: {e}")
            return {
                "total_entities": 0,
                "total_relationships": 0,
                "entity_types": [],
                "extraction_date": datetime.now(timezone.utc).isoformat(),
                "domain": "urban_planning",
                "extraction_method": "mistral_api_llm",
                "error": str(e)
            }


if __name__ == "__main__":
    # Test code
    print("Testing VectorGraphProcessor...")

    # Mock Mistral API for testing
    class MockMistralAPI:
        def run_command(self, prompt, max_tokens=500, temperature=0.2):
            if "ENTITIES" in prompt:
                return """
                ENTITIES
                ========

                cities_places:
                - London
                - Docklands
                - Canary Wharf

                transport_planning:
                - DLR
                - Light Rail
                - Public Transit

                urban_concepts:
                - Transit-Oriented Development
                - Urban Regeneration
                """
            else:
                return """
                RELATIONSHIPS
                ============

                1. FROM: DLR | RELATION: located_at | TO: Docklands
                2. FROM: DLR | RELATION: demonstrates | TO: Transit-Oriented Development
                """

    # Create processor
    mock_api = MockMistralAPI()
    processor = VectorGraphProcessor(mistral_api=mock_api)

    # Test embedding metadata
    print("\n1. Testing create_embedding_metadata:")
    embedding = [0.1] * 1536
    embed_meta = processor.create_embedding_metadata(embedding)
    print(json.dumps(embed_meta, indent=2))

    # Test entity extraction
    print("\n2. Testing extract_entities:")
    entities = processor.extract_entities(
        initial_analysis="London Docklands DLR project...",
        detailed_analysis="Transit-oriented development in London...",
        catalogue_entry="Urban regeneration project..."
    )
    print(json.dumps(entities, indent=2))

    # Test relationship extraction
    print("\n3. Testing extract_relationships:")
    relationships = processor.extract_relationships(
        entities=entities,
        initial_analysis="DLR is located in Docklands...",
        detailed_analysis="The DLR demonstrates TOD principles...",
        catalogue_entry="..."
    )
    print(json.dumps(relationships, indent=2))

    # Test graph metadata
    print("\n4. Testing create_graph_metadata:")
    graph_meta = processor.create_graph_metadata(entities, relationships)
    print(json.dumps(graph_meta, indent=2))

    print("\n✅ Tests completed!")
