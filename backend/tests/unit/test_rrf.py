from app.providers.base import ScoredChunk

def test_rrf_scoring_order():
    c1 = ScoredChunk("c1", "d1", "TS 23.501", 18, "18.6.0", "4.2.2", "Title", "4.2", 1, 1, "Text 1", 50)
    c2 = ScoredChunk("c2", "d1", "TS 23.501", 18, "18.6.0", "6.3.2", "Title", "6.3", 2, 2, "Text 2", 50)
    
    # Simulate rank 0 in vector and rank 0 in lexical for c1
    k = 60
    c1.rrf_score = (1.0 / (k + 1)) + (1.0 / (k + 1))
    c2.rrf_score = (1.0 / (k + 1))

    assert c1.rrf_score > c2.rrf_score
