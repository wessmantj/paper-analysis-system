# test_pipeline.py

from src.pipeline import PaperPipeline

# Initialize pipeline
pipeline = PaperPipeline(
    data_dir='data/raw',
    db_path='data/documents.db',
    log_file='logs/pipeline.log'
)

# Process all PDFs
pipeline.process_all_pdfs()

# Get statistics
stats = pipeline.get_statistics()

print("\n" + "="*60)
print("FINAL STATISTICS")
print("="*60)
print(f"Total PDFs: {stats['total']}")
print(f"Successful: {stats['successful']}")
print(f"Failed: {stats['failed']}")
print(f"Success rate: {stats['successful']/stats['total']*100:.1f}%")
print("="*60)