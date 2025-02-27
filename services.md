# Document Processing System Architecture

## Overview

The document processing system in our application is designed to extract, process, and vectorize content from PDF documents. This enables semantic search and AI-powered interactions with the document content. The system consists of several specialized services that work together to handle different aspects of document processing.

---

## Core Services

### 1. FileProcessorService

**Purpose:**  
Orchestrates the entire document processing workflow.

**Key Functionality:**
- Loads PDF documents using either PyPDF2 or Google Drive.
- Coordinates the extraction, splitting, and storage of document content.
- Manages document processing status.
- Handles error recovery and logging.
- Supports two processing paths: traditional (PyPDF2) or enhanced (Google Drive).

**Process Flow (PyPDF2 path):**
1. Retrieves the document by ID and marks it as "processing".
2. Opens and reads the PDF file using PyPDF2.
3. Processes each page sequentially.
4. For each page:
   - Extracts text.
   - Splits it into manageable chunks.
   - Stores each chunk with its vector embedding.
5. Updates document status to "processed" upon completion.

**Process Flow (Google Drive path):**
1. Retrieves the document by ID and marks it as "processing".
2. Uploads the PDF to Google Drive.
3. Converts it to Google Docs format for enhanced text extraction.
4. Downloads the processed text content.
5. Splits the entire document text into chunks.
6. Stores each chunk with its vector embedding.
7. Updates document status to "processed" upon completion.

---

### 2. OpenAIService

**Purpose:**  
Interfaces with OpenAI's API to generate vector embeddings.

**Key Functionality:**
- Creates semantic vector embeddings for text chunks.
- Uses OpenAI's "text-embedding-3-large" model (3072 dimensions).
- Handles API communication and error handling.

**Usage:**  
- Each text chunk is sent to OpenAI's API.
- The returned embedding is a 3072-dimensional vector that represents the semantic meaning of the text.
- These embeddings enable semantic search and similarity comparisons.

---

### 3. TextSplitterService

**Purpose:**  
Divides document text into manageable chunks for processing.

**Key Functionality:**
- Splits text into chunks based on token count.
- Uses tiktoken for accurate tokenization.
- Maintains context with overlapping chunks.

**Configuration:**
- **Default chunk size:** 1000 tokens
- **Default overlap:** 200 tokens
- **Token limit per chunk:** 2000 tokens

**Process:**
1. Tokenizes the input text using tiktoken.
2. Creates chunks that respect token limits.
3. Ensures chunks overlap to maintain context across boundaries.
4. Returns chunks with their token counts.

---

### 4. VectorService

**Purpose:**  
Manages the storage and retrieval of vector embeddings.

**Key Functionality:**
- Stores document chunks with their embeddings in the database.
- Validates embedding dimensions (3072 for text-embedding-3-large).
- Provides semantic search capabilities using vector similarity.

**Key Operations:**
- `store_chunk`: Creates embeddings and stores chunks in the database.
- `search_similar`: Finds semantically similar chunks using cosine similarity.

**Database Integration:**
- Uses Django's transaction management for data integrity.
- Leverages pgvector for efficient vector similarity search.

---

### 5. GoogleDriveService

**Purpose:**  
Provides enhanced text extraction capabilities via Google Drive.

**Key Functionality:**
- Uploads PDFs to Google Drive.
- Converts documents to Google Docs format for improved text extraction.
- Downloads processed text content.
- Manages Google Drive API authentication and file operations.
- Cleans up temporary files from Drive after processing.

**Process Flow:**
1. Uploads PDF to Google Drive.
2. Converts to Google Docs format (better text extraction than PyPDF2).
3. Exports as plain text.
4. Cleans up by deleting temporary files from Drive.
5. Returns extracted text content.

**Benefits over PyPDF2:**
- Better handling of complex layouts and formatting.
- Improved extraction of structured content (e.g., tables, recipes).
- OCR capabilities for scanned documents.
- Better preservation of document structure.

---

## Data Flow

1. **Document Submission:**
   - User submits a document for processing via API.
   - System creates a `StoredDocument` record with "pending" status.
   - User can optionally specify to use Google Drive for enhanced processing.

2. **Text Extraction:**
   - **Google Drive path:** The entire document is processed at once with better text quality.
   - **PyPDF2 path:** The document is processed page by page.

3. **Text Chunking:**
   - `TextSplitterService` divides the extracted text into manageable chunks.
   - Chunks overlap to maintain context across boundaries.

4. **Embedding Generation:**
   - `OpenAIService` creates vector embeddings for each text chunk.
   - Each embedding is a 3072-dimensional vector representing the semantic meaning.

5. **Storage:**
   - `VectorService` stores each chunk with its embedding in the database.
   - `DocumentChunk` records are created with references to their parent document.

6. **Search & Retrieval:**
   - `VectorService` provides semantic search capabilities.
   - Queries are converted to embeddings and compared using cosine similarity.
   - Most similar chunks are returned based on semantic meaning.

---

## Error Handling

- **Comprehensive Logging:**  
  Each service logs detailed error information.
- **Resilience:**  
  Processing continues even if individual chunks or pages fail.
- **Status Updates:**  
  Document status is updated to reflect the processing outcome.
- **Transactions:**  
  Transactions ensure database integrity.

---

## Performance Considerations

- **Sequential Processing:**  
  Processing is done sequentially to manage API rate limits.
- **Chunk Configuration:**  
  Chunk size and overlap are configurable to balance processing speed and context preservation.
- **Vector Search Optimization:**  
  Vector similarity search is optimized using pgvector's indexing capabilities.
- **Enhanced Processing:**  
  Google Drive processing is recommended for complex documents or when higher quality text extraction is needed.

---

This architecture provides a robust foundation for document processing, enabling powerful semantic search and AI-powered interactions with document content.
