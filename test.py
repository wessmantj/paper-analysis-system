# test.py

from src.pipeline import create_database, extract_pdf_text

# Create database first
create_database('data/documents.db')

# Test with your specific PDF
result = extract_pdf_text('data/raw/12889_2020_Article_8969.pdf')

print(f"\n{'='*50}")
print(f"Success: {result['success']}")
print(f"Pages: {result['page_count']}")
print(f"Characters: {len(result['text'])}")
print(f"Error: {result['error']}")
print(f"{'='*50}\n")

print("First 500 characters:")
print(result['text'][:500])

print("\n...\n")

print("Last 500 characters:")
print(result['text'][-500:])

# Test with file that doesn't exist
print("\n" + "="*50)
print("Testing error handling:")
result2 = extract_pdf_text('data/raw/fake_file.pdf')
print(f"Success: {result2['success']}")
print(f"Error: {result2['error']}")