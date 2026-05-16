
import os
import django
import json
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import CitationSource, DocumentAsset

def check_citation():
    key = 'citation-source-1778932926117-2izm53374ka'
    try:
        cs = CitationSource.objects.get(key=key)
        print(f"CitationSource Key: {key}")
        metadata = cs.metadata
        asset_ids = metadata.get('asset_ids', [])
        print(f"Referenced Asset IDs in CitationSource: {asset_ids}")
        
        doc_id = cs.document_id
        current_assets = DocumentAsset.objects.filter(document_id=doc_id, is_deleted=False)
        current_ids = [str(a.id) for a in current_assets]
        print(f"Current valid Asset IDs for Document {doc_id}: {current_ids}")
        
        # Check if they match
        missing = [aid for aid in asset_ids if aid not in current_ids]
        if missing:
            print(f"MISSING ASSETS (Stale IDs): {missing}")
            # Update metadata to use current IDs
            metadata['asset_ids'] = current_ids
            cs.metadata = metadata
            cs.save()
            print("Successfully updated CitationSource metadata with current asset IDs.")
        else:
            print("All referenced assets are valid.")
            
    except CitationSource.DoesNotExist:
        print(f"CitationSource {key} not found.")

if __name__ == "__main__":
    check_citation()
