# debug_pdf.py

from src.pipeline import extract_pdf_text

# Extract text
result = extract_pdf_text('data/raw/12889_2020_Article_8969.pdf')

if result['success']:
    text = result['text']
    
    # Show first 2000 characters
    print("="*60)
    print("FIRST 2000 CHARACTERS OF PDF:")
    print("="*60)
    print(text[:2000])
    print("\n" + "="*60)
    
    # Show all lines (first 50)
    print("\nFIRST 50 LINES:")
    print("="*60)
    lines = text.split('\n')
    for i, line in enumerate(lines[:50]):
        if line.strip():  # Only show non-empty lines
            print(f"Line {i}: '{line.strip()}'")
    
    # Search for "abstract"
    print("\n" + "="*60)
    print("SEARCHING FOR 'ABSTRACT':")
    print("="*60)
    text_lower = text.lower()
    pos = text_lower.find('abstract')
    if pos != -1:
        print(f"✓ Found 'abstract' at position {pos}")
        print(f"Context around it:")
        print(text[max(0, pos-100):pos+200])
    else:
        print("❌ 'abstract' not found in text")
        
        # Try alternative keywords
        keywords = ['summary', 'background', 'introduction', 'overview']
        for keyword in keywords:
            pos = text_lower.find(keyword)
            if pos != -1:
                print(f"\n✓ Found '{keyword}' at position {pos}")
                break