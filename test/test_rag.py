# test_rag.py

from src.pipeline import PaperPipeline

print("="*60)
print("RAG SYSTEM TEST")
print("="*60)

# Initialize pipeline
print("\n1. Initializing pipeline...")
pipeline = PaperPipeline('data/raw', 'data/documents.db', 'logs/rag.log')

# Build RAG index
print("\n2. Building RAG index from database...")
pipeline.build_rag_index()

# Test queries
questions = [
    "What is the effect of physical fitness on health?",
    "What are the effects of testosterone therapy?",
    "How does leptin affect appetite?"
]

print("\n" + "="*60)
print("TESTING QUERIES")
print("="*60)

for question in questions:
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}")
    
    results = pipeline.search(question, top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Paper ID: {result['paper_id']}")
        print(f"    Chunk Index: {result['chunk_index']}")
        print(f"    Distance: {result['distance']:.4f}")
        print(f"    Text Preview: {result['chunk_text'][:200]}...")

print("\n" + "="*60)
print("✓ RAG SYSTEM TEST COMPLETE")
print("="*60)