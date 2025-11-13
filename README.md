# paper-analysis-system
Personal Capstone for wrapping up my introduction to RAG + SQL + Data Pipelines


# RESEACH PAPER ANALYSIS SYSTEM WITH RAG
A production-ready pipeline for processing research papers (PDFs), extracting metadata, and enabling semantic search using Retrieval-Augmented Generation (RAG).

## Overview

This system processes research papers, extracts structured metadata, stores data in SQLite, and provides semantic search capabilities using vector embeddings and FAISS.

**Key Features:**
-  PDF text extraction and metadata parsing
-  SQLite database with structured storage
-  Semantic search using RAG (Retrieval-Augmented Generation)
-  Comprehensive logging and error handling
-  Batch processing with progress tracking

---

##  Architecture
PDF Files → Extract Text → Parse Metadata → Store in SQLite
↓
Chunk Documents
↓
Create Embeddings
↓
Build FAISS Index
↓
Semantic Search
---

##  Features

### 1. **PDF Processing Pipeline**
- Extracts text from research papers
- Parses titles, authors, and abstracts
- Handles errors gracefully with logging
- Progress tracking with tqdm

### 2. **Metadata Extraction**
- Title detection (multi-line support)
- Author identification (with affiliations)
- Abstract extraction (section-based parsing)

### 3. **Database Storage**
- SQLite with normalized schema
- Full-text storage for RAG
- Query by ID or retrieve all papers
- Automatic timestamp tracking

### 4. **RAG System**
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Vector Search:** FAISS IndexFlatL2
- **Chunking:** 1000 chars with 200 overlap
- **Retrieval:** Top-k semantic search

### 5. **Logging & Monitoring**
- Console and file logging
- Processing statistics
- Error tracking with detailed messages

---

