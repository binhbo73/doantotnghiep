
import os
import django
import json
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import DocumentAsset, Document
# Find where Message is stored. Likely in a chat app.
# Based on earlier grep, it might be in an app I haven't seen yet.
# Let's try to import it from common locations.
try:
    from apps.operations.models import Message
except ImportError:
    from django.apps import apps
    Message = apps.get_model('operations', 'Message')

logger = logging.getLogger(__name__)

def migrate_citations():
    messages = Message.objects.filter(role='assistant', citations__isnull=False)
    print(f"Found {messages.count()} assistant messages with citations.")
    
    updated_count = 0
    
    for msg in messages:
        citations = msg.citations
        if not citations: continue
        changed = False
        
        for citation in citations:
            if citation.get('type') == 'asset' or 'asset_id' in citation:
                asset_id = citation.get('asset_id') or citation.get('asset', {}).get('id')
                if not asset_id:
                    continue
                
                # Check if asset exists
                exists = DocumentAsset.objects.filter(id=asset_id, is_deleted=False).exists()
                if not exists:
                    # Find a replacement
                    doc_id = citation.get('document_id')
                    sheet = citation.get('asset_sheet_name') or citation.get('asset', {}).get('sheet_name')
                    anchor = citation.get('asset_anchor_cell') or citation.get('asset', {}).get('anchor_cell')
                    
                    if not doc_id:
                        continue
                    
                    # Special case for the F8 -> G8 shift we know happened
                    search_anchors = [anchor]
                    if anchor == 'F8': search_anchors.append('G8')
                    if anchor == 'F14': search_anchors.append('G14')
                    
                    replacement = DocumentAsset.objects.filter(
                        document_id=doc_id,
                        sheet_name=sheet,
                        anchor_cell__in=search_anchors,
                        is_deleted=False
                    ).first()
                    
                    if replacement:
                        print(f"Updating citation in message {msg.id}: {anchor} -> {replacement.anchor_cell} (ID: {replacement.id})")
                        citation['asset_id'] = str(replacement.id)
                        if 'asset' in citation:
                            citation['asset']['id'] = str(replacement.id)
                            citation['asset']['anchor_cell'] = replacement.anchor_cell
                            citation['asset']['image_url'] = f"/api/v1/assets/{replacement.id}/image"
                            citation['asset']['thumbnail_url'] = f"/api/v1/assets/{replacement.id}/thumbnail"
                        
                        citation['asset_anchor_cell'] = replacement.anchor_cell
                        changed = True
        
        if changed:
            msg.save()
            updated_count += 1
            
    print(f"Finished. Updated {updated_count} messages.")

if __name__ == "__main__":
    migrate_citations()
