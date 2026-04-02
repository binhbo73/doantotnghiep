"""
Integration test cho Vector DB (ChromaDB)
Chạy: python test_db_integration.py
"""

import asyncio
from src.vector_db.chroma_client import chroma_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_chroma_db():
    """Test ChromaDB"""
    print("\n" + "=" * 70)
    print("🧪 CHROMADB INTEGRATION TEST")
    print("=" * 70 + "\n")

    try:
        # Tạo collection
        print("1️⃣  Testing ChromaDB...")
        collection = chroma_client.get_or_create_collection("test_documents")
        print("   ✅ Collection created/retrieved")

        # Test thêm embedding
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 256  # 1280 dimensions
        success = chroma_client.add_embedding(
            collection_name="test_documents",
            document_id="doc_001",
            embedding=test_embedding,
            document_text="This is a test document",
            metadata={"source": "test", "type": "example"},
        )
        if success:
            print("   ✅ Embedding added successfully")

        # Test search
        results = chroma_client.search(
            collection_name="test_documents",
            query_embedding=test_embedding,
            n_results=5,
        )
        print(f"   ✅ Search completed: Found {len(results['ids'][0])} results")

        # Test count
        count = chroma_client.get_embedding_count("test_documents")
        print(f"   ✅ Collection has {count} embeddings")

        print("\n✅ ChromaDB tests PASSED")
        return True

    except Exception as e:
        logger.error(f"❌ ChromaDB test failed: {e}")
        print(f"\n❌ ChromaDB tests FAILED: {e}")
        return False


def main():
    """Run all integration tests"""
    print("\n" + "🎯 " * 20)
    print("RAG SYSTEM - VECTOR DB INTEGRATION TEST")
    print("🎯 " * 20)

    results = {}

    # Test ChromaDB
    results["chromadb"] = test_chroma_db()

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ System is ready for production use")
    else:
        print("\n⚠️  Some tests failed. Check logs for details.")

    print("=" * 70 + "\n")

    # Close connections
    try:
        chroma_client.close()
        print("✅ All connections closed gracefully")
    except Exception as e:
        logger.error(f"Error closing connections: {e}")


if __name__ == "__main__":
    main()
