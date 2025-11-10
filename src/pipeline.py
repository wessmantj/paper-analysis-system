# This is where the PDF files get text extracted -> Parsed Metadata -> Stored in SQLite -> and Logged

import os
import sqlite3
from pypdf import PdfReader
import logging
from datetime import datetime
import numpy as np # Array operations for embedding
from sentence_transformers import SentenceTransformer 
import faiss

# Global embedding model - only loads once and can be used everywhere
EMBEDDING_MODEL = None

def get_embedding_model():
    """
    Get or create the embedding model (singleton pattern)
    
    Returns:
        SentenceTransformer model
    """
    global EMBEDDING_MODEL
    if EMBEDDING_MODEL is None:
        EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return EMBEDDING_MODEL

# This call loads the model in 2-3 seconds then can get used instanly by other functions
    

# Create the documents table if it doesn't exist
def create_database(db_path: str):
    '''
    
    Args:
        db_path: Path to SQLite database file (e.g., 'data/documents.db')
    '''

    con = sqlite3.connect(db_path) # creates/connects to database
    cur = con.cursor() # allows command execution in db

    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                full_text TEXT,
                page_count INTEGER,
                file_size INTEGER,
                processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
                )''')
    con.commit() # save changes to database
    con.close() # closes connection

# INTEGER PRIMARY KEY AUTOINCREMENT: Auto-generates unique ID for each paper
# TEXT: Stores strings (no length limit in SQLite)
# TIMESTAMP DEFAULT CURRENT_TIMESTAMP: Automatically sets current date/time
# IF NOT EXISTS: Won't error if table already exists (safe to run multiple times)


def extract_pdf_text(pdf_path: str) -> dict: # Import PDF library

    # Initialize with empty/default values 
    result = {
        'text': '',
        'page_count': 0,
        'success': False,
        'error': None
    }


    try:
        
        # Open the PDF using parameter
        reader = PdfReader(pdf_path)

        # Get number of pages
        result['page_count'] = len(reader.pages)

        # Extract all text from pages
        all_text = []

        for page in reader.pages:
            # Extract text from individual page & add to list
            page_text = page.extract_text() # returns strong of text from that page
            all_text.append(page_text) # append to list all_text

            # Combine all text from list into single string for db
        result['text'] = '\n\n'.join(all_text) # ''.join(list) take list and combines into one string with margin between pages

        result['success'] = True

    except FileNotFoundError:
        # If file doesn't exists
        result['error'] = f"File not found: {pdf_path}"

    except Exception as e:
        # Catches other unexpected errors
        result['error'] = f"Error proccessing PDF: {str(e)}"

    return result


# Extract text and metadata from PDF file
def parse_metadata(full_text: str) -> dict:
    """
    
    Args:
        full_text: Complete text extracted from PDF
        
    Returns:
        dict with keys:
            - 'title': Paper title (str)
            - 'authors': Authors string (str)
            - 'abstract': Abstract text (str or None)
    """   
     
    metadata = {
        'title': '',
        'authors': '',
        'abstract': None,
    }

    # Split text into lines
    lines = full_text.split('\n') # split('\n') breaks text at newline characters

    # Remove whitespace and empty lines
    line = [line.strip() for line in lines if line.strip()] # strip90 removes spaces/tabs from beginning and end
    
    # Debug code for locating metadata

    title_lines = []
    start_index = 0

    # Skip pubmed download headers
    if lines and ('RESEARCH' in lines[0].upper() or 'ARTICLE' in lines[0].upper() or 'ACCESS' in lines[0].upper()):
        start_index = 1
        
    # Collect title lines 1-3 lines before author name
    for i in range(start_index, min(start_index + 5, len(lines))):
        line = lines[i]
        
        # Stop if author line is hit
        if any(char.isdigit() for char in line) and ('*' in line or '@' in line):
            break
        # Stop if line says 'Abstract'
        if line.lower() == 'abstract':
            break
        if len(line) > 10:
            title_lines.append(line)

    # Combine title lines
    metadata['title'] = ' '.join(title_lines) if title_lines else lines[0] if lines else '' # Joined together with spaces for correct formatting

    # Extract authors - look for line with numbers or special characters
    author_lines = []

    for i, line in enumerate(lines[:20]): # Check first 20 lines
        # Author lines usually have numbers, astericks, commas
        if any(char.isdigit() for char in line) and (',' in line or '*' in line):
            author_lines = [line]

            if i + 1 < len(lines) and 'and' in lines[i +1].lower():
                author_lines.append(lines[i + 1])
            metadata['authors'] = ' '.join(author_lines)
            break
    
    # Outsorced author detection idea but looks for numerical affiltions ( 1, 2, *)
    # and patterns for seperating names

    # Extract abstract - find "abstract" keyword and get text till next section
    text_lower = full_text.lower()

    # Find header
    abstract_index = -1
    for i, line in enumerate(lines):
        if line.lower() == 'abstract':
            abstract_index = i
            break

    if abstract_index != -1 and abstract_index + 1 < len(lines):
        # Collect lines after abstract until next section header
        abstract_lines = []

        section_headers = ['background', 'introduction', 'methods', 'keywords','correspondence']

        for i in range(abstract_index + 1, len(lines)):
            line = lines[i]
            line_lower = line.lower()

            # Stop at section headers
            if any(header in line_lower for header in section_headers):
                break

            # Stop at short lines/ possible headers
            if len(line) < 20:
                continue

            abstract_lines.append(line)

        if abstract_lines:
            abstract_text = ' '.join(abstract_lines)

            # Clean up
            abstract_text = abstract_text.strip()
            
            # Limit length
            if len(abstract_text) > 100:  # At least 100 chars
                metadata['abstract'] = abstract_text[:3000]  # Max 3000 chars

    return metadata

# Insert paper metadata into database
def insert_paper(db_path: str, paper_data: dict):
    """
    Insert paper metadata into database
    
    Args:
        db_path: Path to SQLite database
        paper_data: dict with keys:
            - filename: str
            - title: str
            - authors: str
            - abstract: str or None
            - full_text: str
            - page_count: int
            - file_size: int (in bytes)
            - status: str ('SUCCESS' or 'ERROR')
    
    Returns:
        int: ID of inserted paper
    """

    # Connect to db and create cursor 
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Prepared INSERT SQL with placeholders
    sql = '''INSERT INTO documents
                (filename, title, authors, abstract, full_text, page_count, file_size, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
    
    # INSERT INTO documents table then each column is a retrieved datapoint from past functions
    # ID isn't included since its generated by the database automatically, along with timestamp
    # Placeholders prevent sql injection and sqlite will safelty insert values were a ? appears

    cur.execute(sql, (
        paper_data['filename'],
        paper_data['title'],
        paper_data['authors'],
        paper_data['abstract'],
        paper_data['full_text'],
        paper_data['page_count'],
        paper_data['file_size'],
        paper_data['status']
    ))
    
    # Execute takes two arguements - SQL statement with placeholders and tuple of values to insert

    # Save changes
    con.commit()

    # Gers ID of most recent insert
    paper_id = cur.lastrowid

    # Close connection to database
    con.close()

    return paper_id

# Retreive all papers from database
def get_all_papers(db_path: str) -> list:

    '''

    Args: 
        db_path : Path to SQLite database
    
    Returns:
        list of dicts, each one containing paper metadata
    '''

    # Connect to database
    con = sqlite3.connect(db_path)
    
    # Set row_factory to enable dictionary access
    con.row_factory = sqlite3.Row

    # Without this rows are returned as Tuples and accessed by index which is difficult to navigate
    # With row_factory they are referred to as objects, accessed by column name

    # Create cursor
    cur = con.cursor()

    # Shows every column from every row in table
    cur.execute("SELECT * FROM documents")
    
    # Fetch all results
    rows = cur.fetchall() # function retreives all matching rows and returns list of row objects

    # Convert Row onjects into regular dicts
    papers = [dict(row) for row in rows]

    # They are converted because row objects are for database while in python its easier to work with dicts broken down is ...

    #  for row in rows:
    #     paper_dict = dict(row)  # Convert Row → dict
    #     papers.append(paper_dict)

    # No changes made so only disconnect from database
    con.close()

    return papers


# Get specific paper by ID
def get_paper_by_id(db_path: str, paper_id: int) -> dict:

    '''

    Args: 
        db_path: Path to the database
        paper_id: ID to specific paper 

    Returns:
        specific paper information based off provided ID
    '''
    # Connect to database
    con = sqlite3.connect(db_path)

    # Set row_factory to enable dictionary access
    con.row_factory = sqlite3.Row
    
    # Create cursor
    cur = con.cursor()

    # SELECT all columns from database where ID matches input
    cur.execute("SELECT * FROM documents WHERE id = ?", (paper_id,))

    # Instead of featching all, only getting one paper/row in database
    row = cur.fetchone()

    # Convert if found
    if row:
        paper = dict(row)
    else:
        paper = None

    con.close()

    return paper

# Logging functions to track pipeline actions

# Configure logger with file and console output
def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Configure logger with file and console output
    
    Args:
        name: Logger name (usually module name like 'PaperPipeline')
        log_file: Optional path to log file (e.g., 'logs/pipeline.log')
        
    Returns:
        Configured logger instance
        
    Example:
        logger = setup_logger('PaperPipeline', 'logs/pipeline.log')
        logger.info('Processing started')
        logger.error('Something went wrong')
    """

    # Create logger
    logger = logging.getLogger(name) # Creates or retreives logger

    # Set logging level
    logger.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # This controls how the messages look
    # %(asctime)s   → Timestamp 
    # %(name)s      → Logger name 
    # %(levelname)s → Level (INFO, ERROR, etc.)
    # %(message)s   → Your actual message

    # Console handler - prints to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Only INFO and above shared to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # StreamHandler outputs to terminal
    # Set level INFO to avoid cluttering with messages

    return logger

# RAG Implimentation - functions for retrieval, augementation and generation

# Convert list of text chunks into embeddings
def create_embeddings(texts: list) -> np.ndarray:
    """
    Args:
        texts: List of text strings to embed

    Returns:
        numpy array of embeddings
    """

    # Get model from original load
    model = get_embedding_model()

    # Create embeddings
    embeddings = model.encode(texts)
    # model.encoe() takes list of strings and retunrs numpy array of shape (len(texts), 384) meaning each row is a 384-dimensional vector for one text

    return embeddings

    

# Split text into overlapping chunks
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
        Args:
            text: Full text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
    
    chunks =[]
    start = 0
    step = chunk_size - overlap # How far to move each time

    while start < len(text):
        # Extract chunk from start to start + chunk_size
        end = start + chunk_size
        chunk = text[start:end]

        # Moving 800 char forward each time, keeping 200 overlap

        chunk.append(chunk)

        # Move to next position
        start += step


    return chunks

# Build FIASS vector store from papers
def build_vector_store(paper_texts: list) -> tuple:
    """
    Args:
        paper_texts: List of (paper_id, full_text) tuples

    Returns:
        (faiss_index, check_metadata) tuple
        chunk_metadata: List of dicts with {paper_id, chunk_text, chunk_index}
    
    """

    all_chunks = []
    chunk_metadata = []

    # Chunk all papers is step 1
    for paper_id, text in paper_texts:
        chunks = chunk_text(text)

        for chunk_index, chunk_text_str in enumerate(chunks):
            all_chunks.append(chunk_text_str)

            chunk_metadata.append({
                'paper_id': paper_id,
                'chunk_text': chunk_text_str,
                'chunk_index': chunk_index
            })

            # Stored metadata for each chunk
            # When FAISS returns index 5, we can lookup the metadata[5]
            # To see which paper and which chunk within that paper


    print(f"Created {len(all_chunks)} chunks from {len(paper_texts)} papers")

    # Create embeddings for all chunks is step 2
    embeddings = create_embeddings(all_chunks)

    print(f"Created embeddings whip shape: {embedding.shape}")
    # embedding.shape = (num_chunks, 384) each row is embedding for one chunk

    # Build FAISS index for step 3
    dimension = embeddings.shape[1] # 384 for all-MiniLM

    index = faiss.IndexFlatL2(dimension)

    # IndexFlatL2 = brute force search using L2
    # Flat means to checks each vector which is okay with our small amount of data

    # FAISS requires float32
    embeddings_float32 = embeddings.astype('float32')
    index.add(embeddings_float32)

    # add() inserts vectors into the index with an ID
    # the ID's correspond to postions in the chunk_metatdata list

    print(f"Built FAISS index with {index.ntotal} vectors")

    return index, chunk_metadata



# Query RAG system
def query_rag(question: str, faiss_index, chunk_metadata: list, top_k: int = 5):
    """
    Args:
        question: User's input
        faiss_index: FAISS indec
        chunk_metadata: chunk metadata
        top_k: number of chunks to retrieve

    Returns: 
        List of relevent chunks with metadata
    """

# Main pipeline for proccessing research papers
class PaperPipeline: 

    # Initialize pipeline 
    def __init__(self, data_dir: str, db_path: str, log_file: str = None):
        """
        Args:
            data_dir: Directory containing PDF files (e.g., 'data/raw')
            db_path: Path to SQLite database (e.g., 'data/documents.db')
            log_file: Optional log file path (e.g., 'logs/pipeline.log')
        
        Example:
            pipeline = PaperPipeline('data/raw', 'data/documents.db', 'logs/pipeline.log')
        """

        # Store parameters as variables accessable by all methods in class
        self.data_dir = data_dir
        self.db_path = db_path

        # Logging setup
        self.logger = setup_logger('PaperPipeline', log_file)
        self.logger.info(f"Initializing PaperPipeline")
        self.logger.info(f"Data directory: {data_dir}")
        self.logger.info(f"Database: {db_path}")

        # Create database if it doesn't exist
        create_database(self.db_path)
        self.logger.info("Database Ready")

        # Initialize stat tracking
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
    
    # Process single PDF file
    def process_single_pdf(self, pdf_path: str) -> bool:

        # Get file name
        filename = os.path.basename(pdf_path)

        self.logger.info(f"Processing: {filename}")

        # Extract PDF text
        result = extract_pdf_text(pdf_path)

        # If failure, log error, and return False
        if not result['success']:
            self.logger.error(f"Failed to extract {filename}: {result['error']}")
            self.stats['failed'] += 1
            self.stats['errors'].append({'file': filename, 'error': result['error']})
            return False
        
        # Parse metadata with title length limit
        metadata = parse_metadata(result['text'])
        self.logger.info(f"Parsed metadata - Title: {metadata['title'][:50]}")

        # Prepare paper data for database
        paper_data = {
            'filename': filename,
            'title': metadata['title'],
            'authors': metadata['authors'],
            'abstract': metadata['abstract'],
            'full_text': result['text'],
            'page_count': result['page_count'],
            'file_size': os.path.getsize(pdf_path),
            'status': 'SUCCESS'
        }

        # Insert into database
        try:
            paper_id = insert_paper(self.db_path, paper_data)
            self.logger.info(f"Inserted {filename} with ID: {paper_id}")
            self.stats['successful'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Database error for {filename}: {str(e)}")
            self.stats['failed'] += 1
            self.stats['errors'].append({'file': filename, 'error': str(e)})
            return False
        
    # Database inserts should be wrapped in try/except so errors don't crash the whole pipeline

    #Process all PDF's in data directory
    def process_all_pdfs(self):
        """
            
            Uses tqdm for progress bar.
            Logs summary statistics at the end.
            
            Example:
                pipeline = PaperPipeline('data/raw', 'data/documents.db')
                pipeline.process_all_pdfs()
            """
        from tqdm import tqdm

        # Find all PDF files
        pdf_files = [f for f in os.listdir(self.data_dir) if f.endswith('.pdf')]

        # os.listdir returns all files in directory and is filtered to only get files ending in .pdf

        # Update logs with found PDFs or error notice
        self.stats['total'] = len(pdf_files)
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")

        if len(pdf_files) == 0:
            self.logger.warning(f"No PDF files found in {self.data_dir}")
            return
        
        # Process each PDF with progress bar or TQDM
        for filename in tqdm(pdf_files, desc="Processing PDFs"):
            full_path = os.path.join(self.data_dir, filename)
            # os.path.join combines directory + filename
            
            self.process_single_pdf(full_path)
            # tqdm wraps the loop to show progress and desc= sets the description text

        # Log final statistics
        self.logger.info("="*60)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info(f"Total files: {self.stats['total']}")
        self.logger.info(f"Successful: {self.stats['successful']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        
        if self.stats['errors']:
            self.logger.info("Errors encountered:")
            for error in self.stats['errors']:
                self.logger.error(f"  {error['file']}: {error['error']}")
        
        self.logger.info("="*60)

    # Get processing stats
    def get_statistics(self) -> dict:
        """

        Returns:
            dict with keys: total, successful, failed, erros

        Example:
            stats = pipeiline.get_stats()
            print(f"Processed {stats['successful']} papers" )

                
        """
        return self.stats.copy()
    
    # Build RAG index from all papers in database
    def build_rag_index(self):

        # Get all papers from db

        # Build vector store

        # Save index to self.faiss_index, self.chunkl_metadata


    # Seach papers using RAG
    def search(self, question: str, top_k: int = 5):




