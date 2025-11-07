import logging
import re
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global mistral_api will be set by the module that imports this
mistral_api = None

def improve_government_classification(content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced government document classification that uses multiple indicators
    beyond simple keyword matching.
    
    Args:
        content: Document content
        metadata: Document metadata
        
    Returns:
        Dictionary with classification results and confidence score
    """
    logger.info("Performing enhanced government document classification")
    
    # Initialize score and evidence
    gov_score = 0
    evidence = []
    max_score = 100
    
    # 1. Check for official government identifiers in content
    gov_identifiers = [
        "official use only", "government document", "classified", 
        "department of", "ministry of", "agency for", "bureau of",
        "for official use", "government publication", "government circular",
        "policy document", "white paper", "green paper",
        "official memorandum", "government report"
    ]
    
    # More weight for exact phrases that strongly indicate government documents
    strong_indicators = [
        "official government document", "classified document",
        "confidential government", "restricted distribution",
        "not for public release", "internal government use",
        "government confidential", "official use only"
    ]
    
    # Count identifier matches
    identifier_matches = [i for i in gov_identifiers if i.lower() in content.lower()]
    if identifier_matches:
        # Award points for basic identifiers (2 points each)
        gov_score += len(identifier_matches) * 2
        evidence.append(f"Found government identifiers: {', '.join(identifier_matches)}")
    
    # Check for strong indicators (5 points each)
    strong_matches = [i for i in strong_indicators if i.lower() in content.lower()]
    if strong_matches:
        gov_score += len(strong_matches) * 5
        evidence.append(f"Found strong government indicators: {', '.join(strong_matches)}")
    
    # 2. Check for government department names with weight by specificity
    gov_departments = {
        # Generic departments (2 points)
        "department of transportation": 2,
        "department of housing": 2,
        "ministry of planning": 2,
        "urban planning authority": 2,
        
        # Specific departments (4 points)
        "department of housing and urban development": 4,
        "ministry of infrastructure and transport": 4,
        "federal highway administration": 4,
        "national planning commission": 4,
        
        # Very specific government entities (6 points)
        "greater london authority planning department": 6,
        "european commission directorate-general for regional policy": 6
    }
    
    for dept, points in gov_departments.items():
        if dept.lower() in content.lower():
            gov_score += points
            evidence.append(f"Found government department reference: '{dept}'")
    
    # 3. Check document formatting patterns typical for government documents
    gov_patterns = [
        (r"section \d+\.\d+", "Structured section numbering"),
        (r"approved by:.*?director", "Approval signature block"),
        (r"reference number:.*?[A-Z0-9-]+", "Government reference number"),
        (r"distribution list:.*?(department|ministry|agency)", "Government distribution list"),
        (r"(public|restricted|confidential|secret).*?classification", "Security classification marking")
    ]
    
    import re
    for pattern, description in gov_patterns:
        if re.search(pattern, content.lower()):
            gov_score += 3
            evidence.append(f"Found government document pattern: {description}")
    
    # 4. Check metadata for government indicators
    meta_indicators = {
        "Author": ["department", "ministry", "government", "agency", "commission"],
        "Publisher": ["government", "department", "ministry", "agency", "commission"],
        "Keywords": ["government", "official", "policy", "regulation"],
        "Subject": ["government", "policy", "regulation", "official"]
    }
    
    for field, indicators in meta_indicators.items():
        field_value = metadata.get(field, "")
        if isinstance(field_value, str):
            for indicator in indicators:
                if indicator.lower() in field_value.lower():
                    gov_score += 2
                    evidence.append(f"Metadata '{field}' contains government indicator: '{indicator}'")
    
    # 5. Check for policy language typical in government documents
    policy_language = [
        "hereby enacted", "in accordance with regulation", "statutory requirement",
        "policy guideline", "mandated by", "regulatory framework",
        "government initiative", "public sector", "statutory obligation"
    ]
    
    policy_matches = [p for p in policy_language if p.lower() in content.lower()]
    if policy_matches:
        gov_score += len(policy_matches) * 2
        evidence.append(f"Found government policy language: {', '.join(policy_matches[:3])}...")
    
    # 6. Context analysis - paragraphs discussing government actions (not just mentioning)
    # Extract paragraphs containing "government" and check for action verbs
    import re
    gov_paragraphs = re.findall(r'[^.!?]*?government[^.!?]*[.!?]', content, re.IGNORECASE)
    
    action_verbs = ["approved", "implemented", "enacted", "established", "regulated", 
                    "mandated", "funded", "published", "authorized", "commissioned"]
    
    contextual_score = 0
    for paragraph in gov_paragraphs[:5]:  # Check up to 5 paragraphs
        for verb in action_verbs:
            if verb.lower() in paragraph.lower():
                contextual_score += 1
                # Only count each paragraph once
                break
    
    if contextual_score > 0:
        gov_score += contextual_score * 3
        evidence.append(f"Found {contextual_score} paragraphs with government actions")
    
    # 7. Calculate confidence and final classification
    confidence = min(gov_score, max_score) / max_score
    
    # Classify based on threshold and confidence
    threshold_government = 0.35  # At least 35% confidence to be government
    
    classification = {
        "is_government": confidence >= threshold_government,
        "confidence": f"{confidence:.2%}",
        "evidence": evidence,
        "score": gov_score,
        "classification": "Government" if confidence >= threshold_government else "Not Government"
    }
    
    logger.info(f"Government classification: {classification['classification']} (confidence: {classification['confidence']})")
    return classification

def analyze_personal_vs_professional(content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced classification system to distinguish between personal and professional documents
    using multiple weighted factors.
    
    Args:
        content: Document content
        metadata: Document metadata
        
    Returns:
        Dictionary with classification results and confidence scores
    """
    logger.info("Performing personal vs. professional classification")
    
    # Initialize scores
    professional_score = 0
    personal_score = 0
    evidence = {
        "professional": [],
        "personal": []
    }
    max_score = 100
    
    # 1. Professional Terminology and Jargon
    professional_terms = [
        "pursuant to", "aforementioned", "hereby", "herein", "deliverable", 
        "stakeholder", "implementation", "framework", "methodology", "strategic",
        "initiative", "objectives", "compliance", "governance", "infrastructure",
        "assessment", "organizational", "protocol", "procurement", "stakeholders"
    ]
    
    professional_term_count = sum(1 for term in professional_terms if term.lower() in content.lower())
    if professional_term_count > 0:
        # Award points based on density of professional terms
        term_score = min(professional_term_count * 2, 20)  # Cap at 20 points
        professional_score += term_score
        evidence["professional"].append(f"Found {professional_term_count} professional terms/jargon")
    
    # 2. Document Structure Analysis
    # Professional documents often have formal sections
    structure_patterns = [
        # Headers, sections, formal elements
        (r"executive summary", 5),
        (r"introduction|background|context", 3),
        (r"methodology|approach", 4),
        (r"conclusion|recommendations", 3),
        (r"appendix|annex", 4),
        (r"references|bibliography", 4),
        # Formatting elements common in professional docs
        (r"table of contents", 5),
        (r"figure \d+[\.:]|table \d+[\.:]", 4),
        (r"page \d+ of \d+", 4)
    ]
    
    for pattern, points in structure_patterns:
        if re.search(pattern, content.lower()):
            professional_score += points
            evidence["professional"].append(f"Found professional document structure: {pattern}")
    
    # 3. Personal Content Indicators
    personal_indicators = [
        # Personal references
        (r"(^|\s)i('m| am| was| have| will)", 3),  # First person with verbs
        (r"my (wife|husband|partner|child|son|daughter|mom|dad|family)", 5),
        (r"(birthday|anniversary|vacation|holiday) (photos|pictures|trip|celebration)", 4),
        # Informal language
        (r"(thanks|thank you|cheers|best wishes|love)", 2),
        (r"(haha|lol|omg|btw|fyi)", 5),  # Informal abbreviations
        (r"(😊|😀|😄|👍|❤️)", 5),  # Emojis
        # Personal activities
        (r"(went|going) (to|on) (dinner|lunch|movie|vacation|trip)", 3),
        (r"(watched|saw|enjoyed) (movie|show|game|match)", 3)
    ]
    
    for pattern, points in personal_indicators:
        matches = re.finditer(pattern, content.lower())
        match_count = sum(1 for _ in matches)
        if match_count > 0:
            score = min(match_count * points, 15)  # Cap at 15 points
            personal_score += score
            evidence["personal"].append(f"Found personal content indicators: {pattern}")
    
    # 4. Analyze Greeting and Sign-off
    # Professional: "Dear Sir/Madam", "To Whom It May Concern", "Sincerely", "Regards"
    # Personal: "Hey", "Hi there", "Love", "Cheers", "XOXO"
    
    professional_greetings = [
        r"dear (sir|madam|dr\.|\w+\s+\w+)",
        r"to whom it may concern",
        r"(sincerely|yours truly|regards|respectfully|cordially)"
    ]
    
    personal_greetings = [
        r"(hey|hi|hello|yo) (\w+)?!*",
        r"(love|hugs|kisses|xoxo|take care|warmly)",
        r"(see you|talk soon|missing you)"
    ]
    
    for greeting in professional_greetings:
        if re.search(greeting, content.lower()):
            professional_score += 3
            evidence["professional"].append(f"Found professional greeting/sign-off: {greeting}")
    
    for greeting in personal_greetings:
        if re.search(greeting, content.lower()):
            personal_score += 3
            evidence["personal"].append(f"Found personal greeting/sign-off: {greeting}")
    
    # 5. Email Header Analysis (if present)
    if "From:" in content and "To:" in content:
        # Check for organization domains
        org_domains = [".org", ".gov", ".edu", ".com"]
        if any(domain in content.lower() for domain in org_domains):
            # More points if both From and To have org domains
            if any(f"from:.*{domain}" in content.lower() for domain in org_domains) and \
               any(f"to:.*{domain}" in content.lower() for domain in org_domains):
                professional_score += 6
                evidence["professional"].append("Both sender and recipient use organizational email domains")
            else:
                professional_score += 3
                evidence["professional"].append("Email contains organizational domain")
    
    # 6. Check metadata for indicators
    if "Author" in metadata:
        # Professional titles in author field
        if re.search(r"(dr|prof|phd|md|esq|director|manager)", str(metadata.get("Author", "")).lower()):
            professional_score += 4
            evidence["professional"].append("Author metadata contains professional title")
    
    # Check for company/organization in metadata
    org_indicators = ["Company", "Organization", "Department", "Division"]
    for indicator in org_indicators:
        if metadata.get(indicator, ""):
            professional_score += 4
            evidence["professional"].append(f"Document metadata contains {indicator} field")
    
    # 7. Decision criteria
    # Calculate and normalize scores
    professional_percentage = min(professional_score, max_score) / max_score
    personal_percentage = min(personal_score, max_score) / max_score
    
    # Determine classification based on relative scores
    is_professional = professional_percentage > personal_percentage
    
    # If scores are close, check for professional document templates
    if abs(professional_percentage - personal_percentage) < 0.1:
        # Check for letterhead, logo, etc.
        if re.search(r"(confidential|privileged|company letterhead|official use)", content.lower()):
            is_professional = True
            professional_score += 10
            evidence["professional"].append("Document contains official/formal designation")
    
    # Generate classification result
    classification = {
        "is_professional": is_professional,
        "professional_confidence": f"{professional_percentage:.2%}",
        "personal_confidence": f"{personal_percentage:.2%}",
        "professional_score": professional_score,
        "personal_score": personal_score,
        "evidence": evidence,
        "classification": "Professional" if is_professional else "Personal"
    }
    
    logger.info(f"Personal vs. Professional classification: {classification['classification']} " +
                f"(Professional: {classification['professional_confidence']}, " +
                f"Personal: {classification['personal_confidence']})")
    
    return classification

class UrbanPlanningAnalysis:
    """Analyzes urban planning documents with content-based analysis."""

    def __init__(self, mistral_api=None):
        if mistral_api is None:
            raise ValueError("mistral_api must be provided")
        self.mistral_api = mistral_api

    # Keywords for content categorization
    KEYWORDS = {
        "urban_planning": [
            "city development", "zoning", "infrastructure", "urban design",
            "land use", "planning policy", "sustainable development"
        ],
        "transportation": [
            "public transit", "traffic management", "sustainable mobility",
            "transport infrastructure", "pedestrian", "cycling"
        ],
        "geography": [
            "spatial analysis", "land use", "environmental factors",
            "geographic information", "mapping", "spatial planning"
        ],
        "technical": [
            "methodology", "analysis", "data", "research",
            "survey", "statistics", "assessment"
        ],
        "policy": [
            "regulation", "policy", "guidelines", "standards",
            "requirements", "legislation", "compliance"
        ]
    }

    def analyze_document(self, content: str, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Main document analysis method with added content extraction."""
        logger.info("Starting document analysis")
        content = self._clean_text_for_analysis(content)
        
        try:
            # Extract authors and title from content
            content_extracted = self._extract_content_authors_and_title(content)
            
            # Generate initial analysis
            initial_analysis = self._generate_initial_analysis(content, content_analysis)
            if initial_analysis.startswith("Error:"):
                logger.error(f"Initial analysis failed: {initial_analysis}")
                return {
                    "error": initial_analysis,
                    "fallback_analysis": self._fallback_analysis(content)
                }

            # Generate detailed analysis
            detailed_analysis = self._generate_detailed_analysis(
                content, content_analysis, initial_analysis)
                
            if detailed_analysis.startswith("Error:"):
                logger.error(f"Detailed analysis failed: {detailed_analysis}")
                return {
                    "error": detailed_analysis,
                    "fallback_analysis": self._fallback_analysis(content)
                }

            # Determine document type
            classification = self._determine_document_type(detailed_analysis)
            
            # Generate enhanced catalogue entry with metadata and content-extracted info
            catalogue_entry = self._generate_catalogue_entry(
            content=content, 
            detailed_analysis=detailed_analysis,
            classification=classification,
            metadata=content_analysis,
            content_extracted=content_extracted
        )

            # Generate fine-tuning analysis types
            logger.info("Generating writing style analysis...")
            writing_style_analysis = self._analyze_writing_style(content)
            
            logger.info("Extracting analytical frameworks...")
            analytical_frameworks = self._extract_analytical_frameworks(content, detailed_analysis)
            
            logger.info("Generating QA pairs...")
            qa_pairs = self._generate_qa_pairs(content, detailed_analysis, classification)
            
            logger.info("Extracting comparative analyses...")
            comparative_analyses = self._extract_comparative_analysis(content, detailed_analysis)

            # Check if document is authored by Peter Hall
            is_hall_document = 0
            
            # Check metadata author
            metadata_author = content_analysis.get('Author', '')
            if isinstance(metadata_author, str) and ('hall' in metadata_author.lower() or 'peter hall' in metadata_author.lower()):
                logger.info(f"Hall document detected from metadata author: {metadata_author}")
                is_hall_document = 1

            # Check content-derived authors
            if not is_hall_document:
                content_author = content_extracted.get('content_authors', '')
                if isinstance(content_author, str) and ('hall' in content_author.lower() or 'peter hall' in content_author.lower()):
                    logger.info(f"Hall document detected from content author: {content_author}")
                    is_hall_document = 1

            # Check catalogue entry
            if not is_hall_document and isinstance(catalogue_entry, str):
                catalogue_lower = catalogue_entry.lower()
                if ('metadata author(s): peter hall' in catalogue_lower or 
                    'content-derived author(s): peter hall' in catalogue_lower or 
                    'author(s): peter hall' in catalogue_lower or 
                    'author: peter hall' in catalogue_lower):
                    logger.info(f"Hall document detected from catalogue entry")
                    is_hall_document = 1

            logger.info(f"Final is_hall_document value: {is_hall_document}")

            final_result = {
                'initial_analysis': initial_analysis,
                'detailed_analysis': detailed_analysis,
                'classification': classification,
                'catalogue_entry': catalogue_entry,
                'content_title': content_extracted['content_title'],
                'content_authors': content_extracted['content_authors'],
                'writing_style_analysis': writing_style_analysis,
                'analytical_frameworks': analytical_frameworks,
                'qa_pairs': qa_pairs,
                'comparative_analyses': comparative_analyses,
                'is_hall_document': is_hall_document
            }
            
            logger.info("Document analysis completed successfully")
            return final_result
                
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "fallback_analysis": self._fallback_analysis(content)
            }
        
    def _extract_content_authors_and_title(self, content: str) -> Dict[str, Any]:
        prompt = f"""
        Analyze the first page to identify:
        1. Document title
        2. Authors/contributors
        3. Dates: Convert to YYYY-MM-DD format
        - For month/year only: use 01 for day (e.g. "November 2010" -> "2010-11-01")
        - For year only: use 01-01 (e.g. "2010" -> "2010-01-01")
        - For month ranges, use first month (e.g. "April/May 2013" -> "2013-04-01")
        - Preserve full dates if available (e.g. "15 June 2012" -> "2012-06-15")

        Return IN THIS EXACT FORMAT:
        CONTENT_TITLE: [Raw title]
        CONTENT_AUTHORS: [Authors]
        CONTENT_DATE: [Date in YYYY-MM-DD format]

        Text to analyze:
        {content[:2000]}
        """
        
        try:
            result = self.mistral_api.run_command(prompt, max_tokens=300)
            logger.info(f"Mistral raw response: {result}")
            
            content_title = "Not found in document content"
            content_authors = "Not found in document content"
            content_date = "Not found in document content"
            
            for line in result.split('\n'):
                if line.startswith('CONTENT_TITLE:'):
                    content_title = line.replace('CONTENT_TITLE:', '').strip()
                    logger.info(f"Extracted title: {content_title}")
                elif line.startswith('CONTENT_AUTHORS:'): 
                    content_authors = line.replace('CONTENT_AUTHORS:', '').strip()
                    logger.info(f"Extracted authors: {content_authors}")
                elif line.startswith('CONTENT_DATE:'):
                    content_date = line.replace('CONTENT_DATE:', '').strip()
                    logger.info(f"Extracted date: {content_date}")
            
            return {
                'content_title': content_title,
                'content_authors': content_authors,
                'content_date': content_date
            }
            
        except Exception as e:
            logger.error(f"Error extracting content information: {e}")
            return {
                'content_title': "Error in content extraction",
                'content_authors': "Error in content extraction",
                'content_date': "Error in content extraction"
            }

    def _generate_initial_analysis(self, content: str, content_analysis: Dict[str, Any]) -> str:
        """Generate initial analysis focusing on document content."""
        logger.info("Generating initial analysis")

        prompt = f"""
        Analyze this urban planning document to provide a high-level overview in the following format:

        INITIAL ANALYSIS
        ===============

        DOCUMENT SUMMARY
        ---------------
        Main Topic: [Central theme of the document]
        Key Message: [Core argument or main point]
        Document Purpose: [Why this document was created]

        AUDIENCE & SCOPE
        --------------
        Target Readers: [Who is this written for]
        Geographic Focus: [Area covered]
        Time Frame: [Period addressed]

        KEY FINDINGS
        -----------
        Major Points:
        - [First key finding]
        - [Second key finding]
        - [Third key finding]

        SIGNIFICANCE
        -----------
        Planning Impact: [Importance to urban planning]
        Innovation: [New ideas or approaches]
        Context: [How this fits into broader planning]

        Base your analysis only on:

        Document Content (first 2000 characters):
        {content[:2000]}

        Content Analysis Results:
        - Possible Authors: {', '.join(content_analysis.get('possible_authors', ['Unknown']))}
        - Dates Found: {', '.join(str(d) for d in content_analysis.get('possible_dates', ['Unknown']))}
        - Word Count: {content_analysis.get('word_count', 0)}
        """

        result = self.mistral_api.run_command(prompt, max_tokens=400)
        logger.info("Initial analysis completed")
        return result

    def _generate_detailed_analysis(self, content: str, content_analysis: Dict[str, Any], initial_analysis: str) -> str:
        """Generate detailed analysis based on document content."""
        logger.info("Generating detailed analysis")
        
        prompt = f"""
        Create a detailed analysis based STRICTLY on the provided document content. If any section cannot be determined from the document, use "Not specified in document" or "No information available". Do not make assumptions or add information not present in the text.

        DETAILED ANALYSIS
        ================

        RESEARCH METHODOLOGY
        ------------------
        Research Approach: [Only if explicitly stated in document, otherwise "Not specified"]
        Data Sources: [Only sources directly mentioned in document]
        Analysis Methods: [Only methods clearly described in document]
        Theoretical Base: [Only theories/frameworks explicitly referenced]

        KEY CONCEPTS
        -----------
        Urban Planning:
        - [Concept name]: [Brief explanation of how this planning concept is applied in the document]
        - [Concept name]: [Brief explanation of how this planning concept is applied in the document]
        - [Concept name]: [Brief explanation of how this planning concept is applied in the document]
        Note: Only include concepts that are explained or discussed in the document, not just mentioned.

        Transport:
        - [Concept name]: [Brief explanation of how this transport concept is applied in the document]
        - [Concept name]: [Brief explanation of how this transport concept is applied in the document]
        - [Concept name]: [Brief explanation of how this transport concept is applied in the document]
        Note: Use "No transport concepts discussed in document" if none are substantively covered.

        Geography:
        - [Geographic concept/pattern]: [Brief explanation of the geographical principle or pattern]
        - [Spatial relationship]: [Brief explanation of how areas relate to each other]
        - [Geographic distribution]: [Brief explanation of spatial distribution pattern]
        Examples of geographic concepts to look for (only if present in document):
        * Urban-peripheral relationships
        * Spatial patterns of development
        * Geographic barriers or connections
        * Regional economic geography
        * Spatial inequality patterns
        * Geographic clustering
        Note: Focus on geographic concepts and patterns rather than just listing locations.
        If no geographic concepts are discussed (only locations listed), state "No geographic concepts analyzed in document"

        METHODS AND TOOLS
        ---------------
        Primary Methods:
        - [Only methods clearly described in document]
        - [Leave empty if fewer methods found]
        - [Use "Methods not specified" if none found]

        Evidence Types:
        - [Only evidence types explicitly mentioned]
        - [Leave empty if fewer types found]
        - [Use "Evidence types not specified" if none found]

        IMPLEMENTATION
        -------------
        Strategy Planning: [Only if clearly outlined in document, otherwise "Not specified"]
        Execution Tools: [Only tools explicitly mentioned]
        Project Timeline: [Only if timeline is explicitly stated]
        Resource Needs: [Only resources specifically mentioned]

        STAKEHOLDER STRUCTURE
        -------------------
        Primary Actors: [Only stakeholders explicitly named in document]
        Key Roles: [Only roles clearly defined in document]
        Coordination: [Only if coordination methods are explicitly described]
        Governance: [Only if governance structure is clearly stated]

        Use this document content for analysis:
        {content[:3000]}

        Important formatting and content rules:
        1. Only include information explicitly stated in the document
        2. Use "Not specified in document" or similar for missing information
        3. Do not make assumptions or inferences beyond the text
        4. Keep formatting clean with no markdown symbols
        5. Be conservative in analysis - if in doubt, mark as "Not specified"
        6. For concepts, always include a brief explanation of how they are used in the document
        7. Focus on patterns and principles rather than just listing examples
        """

        result = self.mistral_api.run_command(prompt, max_tokens=1000)
        logger.info("Detailed analysis completed")
        return result

    def _determine_document_type(self, detailed_analysis: str) -> str:
        """Determine document type and classification."""
        logger.info("Determining document type")
        
        prompt = f"""
        Create a classification analysis following this exact format, with no markdown symbols, asterisks, or hashtags:

        CLASSIFICATION ANALYSIS
        =====================

        DOCUMENT TYPOLOGY
        ---------------
        Document Class: [Report/Study/Plan/Policy]
        Format Type: [Technical/Academic/Professional]
        Category: [Working Paper/Official Document/Draft]

        TECHNICAL FEATURES
        ----------------
        Writing Style: [Technical/Academic/General]
        Presentation: [How information is presented]
        Reference Format: [Citation and reference style]

        DOCUMENT STRUCTURE
        ----------------
        Organization: [How content is organized]
        Main Sections: [Key document components]
        Format Style: [Layout and presentation approach]

        INTENDED USAGE
        -------------
        Primary Purpose: [Main intended use]
        Target Users: [Intended audience]
        Application: [How document should be used]

        Important: Follow this exact format, using only plain text, with no markdown symbols or formatting characters.
        Use exact spacing and underlines as shown above.
        """

        result = self.mistral_api.run_command(prompt, max_tokens=400)
        logger.info("Document type determination completed")
        return result

    def _generate_catalogue_entry(self, content: str, detailed_analysis: str, classification: str, metadata: Dict[str, Any], content_extracted: Dict[str, Any]) -> str:
        """Generate enhanced catalogue entry with metadata."""
        logger.info("Generating detailed catalogue entry")
        logger.info(f"Creating catalogue entry with content_extracted: {content_extracted}")
        
        # First, determine confidentiality level using specific categories only
        confidentiality_prompt = f"""
        Analyze this document to determine its confidentiality level. Consider all aspects:

        Document Content Preview: {content[:2000]}
        Detailed Analysis: {detailed_analysis}
        Classification: {classification}

        For each category below, look for SPECIFIC evidence in the document:

        1. Government confidentiality - REQUIRES at least TWO of the following:
        - Official government letterhead or markings
        - Explicit statements that document is for government use only
        - Internal government policy discussions not meant for public release
        - Confidential government planning information
        - Documents explicitly marked as government sensitive/confidential

        2. Financial confidentiality - REQUIRES at least ONE of the following:
        - Detailed financial statements with non-public figures
        - Specific budget allocations not publicly disclosed
        - Contract monetary values marked as confidential
        - Private financial forecasts or projections
        - Financial data that would cause harm if disclosed

        3. Personal Data confidentiality - REQUIRES at least ONE of the following:
        - Personal identifiable information (names with addresses, phone numbers, etc.)
        - Health information about specific individuals
        - Personal financial details of individuals
        - Employment records with personal details

        4. Contract confidentiality - REQUIRES at least ONE of the following:
        - Contract terms explicitly marked as confidential
        - Non-public contract negotiations
        - Proprietary business arrangements
        - Private contractual obligations

        Classify the document's confidentiality level as one of:
        - None: No sensitive information present as defined above
        - Government: Meets the specific criteria for government confidentiality
        - Financial: Meets the specific criteria for financial confidentiality
        - Personal Data: Meets the specific criteria for personal data confidentiality
        - Contract: Meets the specific criteria for contract confidentiality

        IMPORTANT: If the document has general sensitive information but does NOT clearly meet the SPECIFIC criteria for any of the above categories, you MUST classify it as "None" and explain that the document doesn't meet the threshold criteria.

        If you are unsure or the document contains only general economic data, research, or publicly available information, classify as "None".

        Provide your response in this format:
        CONFIDENTIALITY
        ==============
        Level: [Selected level]
        Reasoning: [Brief explanation with specific evidence or why it doesn't meet criteria]
        Access Restrictions: [Any specific handling requirements, or "Standard handling" if None]
        """
        
        confidentiality_result = self.mistral_api.run_command(confidentiality_prompt, max_tokens=200)
        
        # Extract metadata with fallbacks
        author = metadata.get('Author', metadata.get('author', 'Unknown'))
        creation_date = (metadata.get('Creation Date') or 
                        metadata.get('created') or 
                        metadata.get('content_date') or
                        'Unknown')
        title = metadata.get('Title', metadata.get('title', 'Unknown'))
        
        # Additional metadata
        possible_authors = metadata.get('possible_authors', [])
        content_date = metadata.get('content_date')
        document_date_source = metadata.get('Document Date Source')
        
        # Main catalogue entry prompt
        prompt = f"""
        Create a detailed library catalogue entry for this urban planning document.
        You MUST display these EXACT values in the DOCUMENT IDENTIFICATION section, preserving any prefixes like 'REVISED OUTLINE:':
        - Original Title: {title}
        - Content-Derived Title: {content_extracted['content_title']}
        - Metadata Author(s): {author}
        - Content-Derived Author(s): {content_extracted['content_authors']}
        - Metadata Creation Date: {creation_date}
        - Content-Derived Date: {content_extracted['content_date']}
        
        Use this information:
        Analysis: {detailed_analysis}
        Classification: {classification}
        Confidentiality Assessment: {confidentiality_result}

        Original Metadata:
        - Author: {author}
        - Creation Date: {creation_date}
        - Title: {title}
        - Subject: {metadata.get('Subject', metadata.get('subject', 'Unknown'))}
        - Last Saved By: {metadata.get('Last Saved By', metadata.get('last_saved_by', 'Unknown'))}
        - Comments: {metadata.get('Comments', metadata.get('comments', 'None'))}
        - Possible Authors found in content: {', '.join(possible_authors) if possible_authors else 'None found'}
        - Content Date: {content_date if content_date else 'Not found'}
        - Date Source: {document_date_source if document_date_source else 'Unknown'}

        Content-Extracted Information:
        - Title found in document: {content_extracted['content_title']}
        - Authors found in document: {content_extracted['content_authors']}
        - Date found in document: {content_extracted['content_date']}

        Return catalogue entry in this EXACT format:

        CATALOGUE ENTRY
        ==============

        DOCUMENT IDENTIFICATION
        ---------------------
        Original Title: [Use title from metadata]
        Content-Derived Title: [Use title found in document text]
        Metadata Author(s): [Use author from metadata]
        Content-Derived Author(s): [Use authors found in document text]
        Metadata Creation Date: [Use creation date from metadata]
        Content-Derived Date: [Use exact date text found in document including any prefix]
        Document Type: [Document type from classification]

        GEOGRAPHICAL SCOPE
        ----------------
        Cities: [List all cities mentioned or referenced in the document]
        Countries: [List all countries mentioned or referenced in the document]
        Regional Focus: [Broader geographical regions discussed]

        SUBJECT CLASSIFICATION
        --------------------
        Primary Subject: [Main theme or topic]
        Secondary Subjects:
        - [Second theme or topic]
        - [Third theme or topic]
        - [Fourth theme or topic]

        DESCRIPTION
        ----------
        [A detailed paragraph of 3-5 sentences describing the document. Include what the document covers, 
        its main arguments or findings, any methodologies used, and its significance to urban planning, 
        transport, or geography.]

        KEYWORDS
        --------
        [Comma-separated list of relevant keywords, at least 10 words]

        CLASSIFICATION
        -------------
        Type: [Professional or Personal]
        Confidentiality Level: [Use result from confidentiality assessment]
        Access Restrictions: [Include any specific access or handling requirements]

        NOTES
        -----
        Last Modified: {metadata.get('Modified', metadata.get('modified', 'Unknown'))}
        Last Saved By: {metadata.get('Last Saved By', metadata.get('last_saved_by', 'Unknown'))}
        Comments: {metadata.get('Comments', metadata.get('comments', 'None'))}

        Important instructions:
        1. Keep the exact section formatting
        2. Ensure CLASSIFICATION section includes both Type and Confidentiality Level
        3. Base confidentiality level strictly on the confidentiality assessment
        4. Include specific access restrictions if any were identified
        5. Be thorough but precise in all fields
        6. You MUST preserve exact dates and prefixes in Content-Derived Date
        """

        result = self.mistral_api.run_command(prompt, max_tokens=800)
        logger.info(f"Catalogue entry generated: {result[:100]}...")
        return result

    # ADDED METHODS FOR FINE-TUNING DATA EXTRACTION
    def _analyze_writing_style(self, content: str) -> str:
        """
        Analyze the writing style patterns in the document.
        
        Args:
            content: Document content
            
        Returns:
            String with writing style analysis
        """
        logger.info("Analyzing writing style patterns")
        
        style_prompt = f"""
        Analyze this text to identify its distinctive academic writing style.
        Focus specifically on:

        1. SENTENCE STRUCTURE: Identify 3-5 example sentences that demonstrate typical structure and length
        2. ACADEMIC PHRASES: List 5-10 distinctive academic phrases or terms used
        3. COMPARATIVE FRAMEWORKS: How comparisons between regions, cities, or concepts are structured
        4. EVIDENCE INTEGRATION: How statistics, data, or evidence are incorporated into arguments
        5. ANALYTICAL PATTERNS: Recurring patterns in how analysis or arguments are structured

        Return your analysis in this EXACT format:

        STYLE ANALYSIS
        =============

        SENTENCE STRUCTURE
        ----------------
        Average Length: [Estimated average words per sentence]
        Structure Patterns:
        - [Pattern 1 description]
        - [Pattern 2 description]
        Examples:
        1. "[Example sentence 1]"
        2. "[Example sentence 2]"

        ACADEMIC PHRASES
        --------------
        - "[Phrase 1]" - [Brief context for usage]
        - "[Phrase 2]" - [Brief context for usage]
        [Continue for all identified phrases]

        COMPARATIVE FRAMEWORKS
        -------------------
        Primary Approach: [Main method of comparison]
        Examples:
        1. "[Example comparison 1]"
        2. "[Example comparison 2]"

        EVIDENCE INTEGRATION
        -----------------
        Citation Style: [How evidence is cited]
        Data Presentation: [How data is presented]
        Examples:
        1. "[Example evidence integration 1]"
        2. "[Example evidence integration 2]"

        ANALYTICAL PATTERNS
        ----------------
        Structure:
        - [Pattern 1 description]
        - [Pattern 2 description]
        Flow:
        - [How arguments typically progress]

        Analyze only this content:
        {content[:4000]}
        """
        
        result = self.mistral_api.run_command(
            style_prompt, 
            max_tokens=800,
            temperature=0.2
        )
        
        logger.info("Writing style analysis completed")
        return result

    def _extract_analytical_frameworks(self, content: str, detailed_analysis: str) -> str:
        """
        Extract analytical frameworks from the document.
        
        Args:
            content: Document content
            detailed_analysis: Detailed analysis of the document
            
        Returns:
            String with analytical frameworks
        """
        logger.info("Extracting analytical frameworks")
        
        framework_prompt = f"""
        Identify distinctive analytical frameworks in this urban planning document.
        Focus on extracting 2-4 complete analytical frameworks with these characteristics:

        1. COMPARATIVE ANALYSIS: How regions, cities, or policies are compared
        2. ECONOMIC EVALUATION: How economic performance is evaluated
        3. SPATIAL RELATIONSHIPS: How spatial relationships are analyzed
        4. POLICY ASSESSMENT: How policy impacts are evaluated

        For each framework, provide:
        - A NAME for the framework
        - The STRUCTURE (steps or components)
        - 1-2 EXAMPLES directly from the text
        - The VARIABLES or factors considered

        Return your analysis in this EXACT format:

        ANALYTICAL FRAMEWORKS
        ===================

        FRAMEWORK 1: [Framework Name]
        -------------------------
        Structure:
        - [Step/Component 1]
        - [Step/Component 2]
        - [Step/Component 3]
        Example:
        "[Direct quote showing this framework in use]"
        Variables:
        - [Variable 1]
        - [Variable 2]
        - [Variable 3]

        FRAMEWORK 2: [Framework Name]
        -------------------------
        [Same structure as above]

        Use only frameworks that are clearly demonstrated in these document sections:

        DETAILED ANALYSIS:
        {detailed_analysis[:1500]}

        CONTENT PREVIEW:
        {content[:1000]}
        """
        
        result = self.mistral_api.run_command(
            framework_prompt, 
            max_tokens=800,
            temperature=0.2
        )
        
        logger.info("Analytical frameworks extraction completed")
        return result

    def _generate_qa_pairs(self, content: str, detailed_analysis: str, classification: str) -> str:
        """
        Generate question-answer pairs based on the document.
        
        Args:
            content: Document content
            detailed_analysis: Detailed analysis of the document
            classification: Document classification
            
        Returns:
            String with Q&A pairs
        """
        logger.info("Generating question-answer pairs")
        
        # Extract geographic scope and subject if available
        geo_scope = ""
        subject = ""
        for line in classification.split('\n'):
            if "Geographic Focus" in line:
                geo_scope = line.split(':', 1)[1].strip() if ':' in line else ""
            elif "Primary Subject" in line:
                subject = line.split(':', 1)[1].strip() if ':' in line else ""
        
        qa_prompt = f"""
        Generate 8-10 question-answer pairs based on this document content.
        Include these question types:
        
        1. FACTUAL: Questions about specific data or facts in the document
        2. ANALYTICAL: Questions requiring comparative or analytical thinking
        3. THEORETICAL: Questions connecting content to urban planning or economic theory
        4. METHODOLOGICAL: Questions about research methods or approaches
        5. IMPLICATION: Questions about implications or significance
        
        The geographic focus is: {geo_scope}
        The primary subject is: {subject}
        
        For each Q&A pair:
        - Make the question specific and substantive
        - Write the answer in an academic style matching the document
        - Include relevant data or evidence from the document
        - Use analytical frameworks where appropriate
        - Keep answers detailed but focused (100-200 words each)
        
        Return in this format:
        
        Q1: [Question text]
        A1: [Answer text]
        
        Q2: [Question text]
        A2: [Answer text]
        
        Generate questions based on:
        
        DETAILED ANALYSIS:
        {detailed_analysis[:1500]}
        
        CONTENT PREVIEW:
        {content[:1500]}
        """
        
        result = self.mistral_api.run_command(
            qa_prompt, 
            max_tokens=1500,
            temperature=0.3
        )
        
        logger.info("Question-answer pairs generation completed")
        return result

    def _extract_comparative_analysis(self, content: str, detailed_analysis: str) -> str:
        """
        Extract comparative analysis examples from the document.
        
        Args:
            content: Document content
            detailed_analysis: Detailed analysis of the document
            
        Returns:
            String with comparative analysis examples
        """
        logger.info("Extracting comparative analysis examples")
        
        comparison_prompt = f"""
        Identify 2-4 examples of comparative analysis from this document.
        Focus on passages where there are direct comparisons between:
        
        - Cities or regions (e.g., Madrid vs Barcelona)
        - Time periods (e.g., 1980s vs 1990s)
        - Economic metrics (e.g., GDP vs employment)
        - Policy approaches (e.g., different investment strategies)
        
        For each comparison, provide:
        1. The ENTITIES being compared
        2. The METRICS or factors used for comparison
        3. The CONCLUSION or insight from the comparison
        4. A direct QUOTE containing the comparison
        
        Return your analysis in this EXACT format:
        
        COMPARATIVE ANALYSES
        ==================
        
        COMPARISON 1
        -----------
        Entities: [What's being compared]
        Metrics: [Factors used for comparison]
        Conclusion: [The insight gained]
        Quote:
        "[Direct quote from the document showing the comparison]"
        
        COMPARISON 2
        -----------
        [Same structure as above]
        
        Extract comparative analyses from:
        {detailed_analysis[:1500]}
        
        CONTENT PREVIEW:
        {content[:1500]}
        """
        
        result = self.mistral_api.run_command(
            comparison_prompt, 
            max_tokens=800,
            temperature=0.2
        )
        
        logger.info("Comparative analysis extraction completed")
        return result

    def _fallback_analysis(self, content: str) -> str:
        """Perform basic keyword-based analysis when API fails."""
        logger.info("Performing fallback analysis")
        content = content.lower()
        categories_found = []

        # Analyze content against keywords
        for category, terms in UrbanPlanningAnalysis.KEYWORDS.items():
            matches = [term for term in terms if term in content]
            if matches:
                relevance = len(matches) / len(terms)
                categories_found.append((category, matches, relevance))

        # Generate fallback response
        if not categories_found:
            return "Unable to determine specific categories for this document."

        categories_found.sort(key=lambda x: x[2], reverse=True)
        response = ["Document Analysis (Fallback):"]
        
        for category, matches, relevance in categories_found:
            category_name = category.replace('_', ' ').title()
            response.append(f"\n{category_name} (Relevance: {relevance:.1%})")
            response.append(f"Found concepts: {', '.join(matches)}")

        response.append("\nNote: This is a basic keyword-based analysis due to API unavailability.")
        return '\n'.join(response)

    def _clean_text_for_analysis(self, text: str) -> str:
        """Clean and prepare text for analysis."""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long while preserving context
        if len(text) > 8000:
            text = text[:4000] + "\n...[content truncated]...\n" + text[-4000:]
            
        return text

if __name__ == "__main__":
    # Test code
    test_content = "This document outlines a proposal for sustainable urban development..."
    test_content_analysis = {
        "possible_authors": ["Jane Smith", "John Doe"],
        "possible_dates": ["2023-05-15"],
        "word_count": 1500
    }
    
    analyzer = UrbanPlanningAnalysis()
    result = analyzer.analyze_document(test_content, test_content_analysis)
    
    print("\nTest Analysis Results:")
    for key, value in result.items():
        print(f"\n{key.upper()}:")
        print(value)

