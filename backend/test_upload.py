import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.apps import apps
from services.document_upload_service import DocumentUploadService

def test_upload():
    Account = apps.get_model('users', 'Account')
    admin_user = Account.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found")
        return

    service = DocumentUploadService()
    
    # Create a dummy file
    file_content = b"This is a test document for RAG system."
    uploaded_file = SimpleUploadedFile("test_doc.txt", file_content, content_type="text/plain")
    
    try:
        print(f"Testing upload for user: {admin_user.username}")
        doc = service.upload(
            file=uploaded_file,
            user_id=admin_user.id,
            access_scope='company',
            description="Test upload via script",
            tags=['test', 'script']
        )
        print(f"Upload Success! Document ID: {doc.id}, Status: {doc.status}")
        
        # Check chunks
        DocumentChunk = apps.get_model('documents', 'DocumentChunk')
        chunks = DocumentChunk.objects.filter(document_id=doc.id)
        print(f"Number of chunks created: {chunks.count()}")
        for chunk in chunks:
            print(f" - Chunk {chunk.chunk_index}: {chunk.content[:50]}... (Vector: {chunk.vector_id})")
            
    except Exception as e:
        print(f"Upload Failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_upload()
