# test_metadata.py

from src.pipeline import extract_pdf_text, parse_metadata

# Extract text from a PDF
result = extract_pdf_text('data/raw/12889_2020_Article_8969.pdf')

if result['success']:
    print("✓ PDF text extracted\n")
    
    # Parse metadata
    metadata = parse_metadata(result['text'])
    
    print("="*50)
    print("EXTRACTED METADATA:")
    print("="*50)
    print(f"\nTitle: {metadata['title']}")
    print(f"\nAuthors: {metadata['authors']}")
    print(f"\nAbstract length: {len(metadata['abstract']) if metadata['abstract'] else 0} characters")
    
    if metadata['abstract']:
        print(f"\nAbstract preview (first 200 chars):")
        print(metadata['abstract'][:200])
        print("...")
else:
    print(f"❌ Failed to extract PDF: {result['error']}")