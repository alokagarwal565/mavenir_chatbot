import pytest
from app.services.context_manager import trim_history, build_effective_query
from app.models.schemas import ConversationTurn

def test_trim_history_empty():
    assert trim_history([]) == []

def test_trim_history_under_limit():
    history = [
        ConversationTurn(role="user", content="hello"),
        ConversationTurn(role="assistant", content="hi there")
    ]
    trimmed = trim_history(history)
    assert len(trimmed) == 2

def test_trim_history_over_turn_limit():
    # 8 turns (4 pairs)
    history = []
    for i in range(8):
        role = "user" if i % 2 == 0 else "assistant"
        history.append(ConversationTurn(role=role, content=f"msg {i}"))
    
    trimmed = trim_history(history)
    # Should retain the last 6 turns (indices 2 to 7)
    assert len(trimmed) == 6
    assert trimmed[0].content == "msg 2"
    assert trimmed[-1].content == "msg 7"

def test_trim_history_over_token_limit():
    history = [
        ConversationTurn(role="user", content="a " * 500),      # ~500 tokens
        ConversationTurn(role="assistant", content="b " * 500)  # ~500 tokens
    ]
    trimmed = trim_history(history)
    # The total is ~1000 tokens, which exceeds 800.
    # The while loop breaks at len(history) <= 2, so it will retain the 2 messages
    assert len(trimmed) == 2

def test_build_effective_query():
    history = [
        ConversationTurn(role="user", content="What is AMF?"),
        ConversationTurn(role="assistant", content="AMF is Access and Mobility Management Function.")
    ]
    query = "What does it do?"
    effective = build_effective_query(query, history)
    assert "What does it do? AMF is Access and Mobility Management Function." == effective
