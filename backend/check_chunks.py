import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.documents.models import Document, DocumentChunk
from services.document.parser import DocumentParser

# Tìm document vừa upload
doc = Document.objects.get(id='e979e1e2-1a72-4e0e-9dd3-73b13323b7b5')
print(f'Document: {doc.original_name}')
print(f'File type: {doc.file_type}')
print(f'Status: {doc.status}')
print(f'Chunk count: {doc.metadata.get("chunk_count", 0)}')

# Lấy chunks
chunks = DocumentChunk.objects.filter(document_id=doc.id).order_by('chunk_index')
print(f'\nFound {len(chunks)} chunks in DB')

# Parse lại file để lấy text gốc
parser = DocumentParser(use_cache=False)  # Không dùng cache để đảm bảo
file_path = f'/app/{doc.storage_path}'
text, meta = parser.parse_file(file_path, file_type=doc.mime_type)
print(f'\nParsed text length: {len(text)} chars')
print(f'Word count: {meta.get("word_count", 0)}')

# Hiển thị text gốc
print('\n=== ORIGINAL TEXT ===')
print(text[:1000] + '...' if len(text) > 1000 else text)

# Hiển thị chunks
print('\n=== CHUNKS CONTENT ===')
for i, chunk in enumerate(chunks):
    print(f'\nChunk {i+1} (token_count: {chunk.token_count}):')
    print(f'"{chunk.content[:300]}..."')
    print(f'Length: {len(chunk.content)} chars')

    # Kiểm tra chunk có trong text gốc không
    if chunk.content.strip() in text:
        print('✅ Chunk matches original text')
    else:
        print('❌ Chunk does NOT match original text')

print('\n=== CHUNK BOUNDARIES ===')
cursor = 0
for i, chunk in enumerate(chunks):
    chunk_start = text.find(chunk.content.strip(), cursor)
    if chunk_start != -1:
        chunk_end = chunk_start + len(chunk.content.strip())
        print(f'Chunk {i+1}: chars {chunk_start}-{chunk_end}')
        cursor = chunk_end
    else:
        print(f'Chunk {i+1}: NOT FOUND in text')