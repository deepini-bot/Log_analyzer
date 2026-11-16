from app.knowledge import KnowledgeBase

def test_chunk_text_splits_long_content():
    chunks=KnowledgeBase.chunk_text(('database timeout. ' * 150),chunk_size=300,overlap=40)
    assert len(chunks)>1
    assert all(chunks)

def test_empty_document_returns_no_chunks():
    assert KnowledgeBase.chunk_text('   ')==[]
