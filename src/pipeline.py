# This is where the PDF files get text extracted -> Parsed Metadata -> Stored in SQLite -> and Logged

import sqlite3
from pypdf import PdfReader

# Create the documents table if it doesn't exist
def create_database(db_path: str):
    '''
    
    Args:
        db_path: Path to SQLite database file (e.g., 'data/documents.db')
    '''

    con = sqlite3.connect('documents.db') # creates/connects to database
    cur = con.cursor() # allows command execution in db

    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                full_text TEXT,
                page_counter INTEGER,
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
    sql = '''("INSERT INTO documents
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
    cur.execute("SELECT * FROM documents WHERE id = ?", (paper_id))

    # Instead of featching all, only getting one paper/row in database
    row = cur.fetchone()

    # Convert if found
    if row:
        paper = dict(row)
    else:
        paper = None

    con.close()

    return paper





