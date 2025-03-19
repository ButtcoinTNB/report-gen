# AI Service Implementation

This document explains how AI services are implemented in the Insurance Report Generator application, including integration with external AI models, prompt engineering patterns, and optimization techniques.

## Overview

The AI functionality in this application utilizes external Large Language Models (LLMs) through API integrations to process document content, extract structured information, and generate professional reports. The primary AI capabilities include:

1. **Document Analysis**: Extracting relevant information from uploaded documents
2. **Information Structuring**: Organizing extracted information into structured formats
3. **Report Generation**: Creating comprehensive reports based on document analysis
4. **Report Refinement**: Refining reports based on user feedback

## AI Service Architecture

The AI functionality is implemented through several components:

### Core Components

- `backend/services/ai_service.py`: Primary interface for AI operations
- `backend/services/pdf_extractor.py`: Handles document text extraction
- `backend/services/multimodal_processor.py`: Processes different types of content (text, images)
- `backend/api/generate.py`: API endpoints that leverage AI services

### Integration with External AI Providers

The application uses OpenRouter API as a gateway to access various AI models:

- Primary model: `google/gemini-2.0-pro`
- Fallback models:
  - `anthropic/claude-3-sonnet-20240229`
  - `openai/gpt-4-turbo-2024-04-09`

## Key AI Functionality

### Variable Extraction (`extract_template_variables`)

This function analyzes documents to extract structured information:

```python
async def extract_template_variables(document_content, additional_info=""):
    """
    Extracts structured variables from document content.
    
    Args:
        document_content: Text content from documents
        additional_info: Additional context provided by the user
        
    Returns:
        Dictionary with extracted variables and fields needing attention
    """
    # Implementation details...
```

**Process:**
1. Prepare prompt with document content and extraction instructions
2. Make API call to AI model
3. Parse and validate the JSON response
4. Return structured data

### Report Generation (`generate_report_text`)

This function creates full report content based on extracted variables:

```python
async def generate_report_text(variables, template=None, additional_info=""):
    """
    Generates report text based on extracted variables and templates.
    
    Args:
        variables: Dictionary of extracted variables
        template: Optional template to follow
        additional_info: Additional context provided by the user
        
    Returns:
        Generated report text
    """
    # Implementation details...
```

**Process:**
1. Combine variables, template examples, and additional info
2. Structure a detailed prompt with formatting instructions
3. Make API call to AI model
4. Process and format the response
5. Return formatted report text

### Report Refinement (`refine_report_text`)

This function updates report content based on user feedback:

```python
async def refine_report_text(report_content, instructions):
    """
    Refines existing report based on user instructions.
    
    Args:
        report_content: Existing report content
        instructions: User instructions for changes
        
    Returns:
        Updated report content
    """
    # Implementation details...
```

**Process:**
1. Create a prompt with current report and refinement instructions
2. Make API call to AI model
3. Validate and format the response
4. Return updated report content

## Prompt Engineering Patterns

The application uses several prompt engineering techniques:

### Few-Shot Learning

Example:
```
Here are examples of well-formatted insurance reports:

Example 1:
[Example report with proper formatting]

Example 2:
[Another example with different structure]

Please generate a report following these examples, using the information below:
[Extracted variables and additional context]
```

### Structured Output Format

Example:
```
Extract the following information from the document content. 
Return your response in JSON format with these keys:
{
  "customer_name": "Full name of the customer",
  "policy_number": "Insurance policy number",
  "incident_date": "Date of the incident (YYYY-MM-DD)",
  "claim_amount": "Total claim amount as decimal"
}
```

### Chain-of-Thought Prompting

Example:
```
Analyze the document step by step:
1. Identify the policy holder information
2. Extract the incident details
3. Determine damage descriptions
4. Calculate the total claim amount
5. Format all information into a structured report
```

## Optimization Techniques

### Content Chunking

For long documents, the application splits content into manageable chunks:

```python
def chunk_content(content, max_chunk_size=8000, overlap=200):
    """Split long content into overlapping chunks for processing"""
    # Implementation...
```

### Parallel Processing

For multiple documents, the application processes them in parallel:

```python
async def process_multiple_documents(document_paths):
    """Process multiple documents in parallel"""
    tasks = [process_document(path) for path in document_paths]
    results = await asyncio.gather(*tasks)
    return results
```

### Caching

The application caches extraction results to avoid redundant processing:

```python
@lru_cache(maxsize=100)
def get_cached_extraction(document_id):
    """Retrieve cached extraction results"""
    # Implementation...
```

### Error Recovery

The application implements fallback strategies for AI service failures:

```python
async def call_ai_with_fallback(prompt, max_retries=3):
    """Call AI service with retry and fallback mechanism"""
    # Implementation with retry logic and fallback models
```

## Security Considerations

The AI integration includes several security measures:

1. **Content Filtering**: Potentially sensitive information is filtered before sending to external AI services
2. **Prompt Sanitization**: User inputs are sanitized before inclusion in prompts
3. **Response Validation**: AI responses are validated to ensure they contain only appropriate content
4. **API Key Security**: API keys are stored securely as environment variables

## Cost Optimization

To optimize costs when working with commercial AI services:

1. **Token Optimization**: Prompts are designed to minimize token usage
2. **Model Selection**: The appropriate model is selected based on task complexity
3. **Caching**: Frequent or identical requests are cached to reduce API calls
4. **Batch Processing**: Multiple operations are batched when possible

## Testing AI Components

The application includes testing strategies for AI components:

1. **Unit Tests**: Testing AI service functions with mock API responses
2. **Integration Tests**: Testing the full AI pipeline with sample documents
3. **Prompt Regression Tests**: Ensuring prompt changes don't degrade output quality

Example test:
```python
def test_variable_extraction():
    """Test that variable extraction produces expected output"""
    test_content = "Sample document with customer John Smith, policy #12345"
    result = extract_template_variables(test_content)
    assert "customer_name" in result
    assert result["customer_name"] == "John Smith"
```

## Extending AI Capabilities

Guidelines for extending the AI functionality:

1. Add new functions to `ai_service.py` for new capabilities
2. Implement proper error handling and fallback strategies
3. Document prompt patterns and expected outputs
4. Consider token usage and performance implications
5. Add appropriate tests for new functionality 