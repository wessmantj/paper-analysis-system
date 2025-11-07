# test_rag.py

from src.pipeline import PaperPipeline

# Initialize pipeline
pipeline = PaperPipeline('data/raw', 'data/documents.db', 'logs/rag.log')

# Build RAG index
print("Building RAG index...")
pipeline.build_rag_index()

# Test queries
questions = [
    "What is the effect of physical fitness on health?",
    "What are the effects of testosterone therapy?",
    "How does leptin affect appetite?"
]

for question in questions:
    print(f"\nQuestion: {question}")
    results = pipeline.search(question, top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Paper ID: {result['paper_id']}")
        print(f"    Chunk: {result['text'][:200]}...")