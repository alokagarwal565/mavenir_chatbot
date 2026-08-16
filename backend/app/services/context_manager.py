from typing import List
from app.models.schemas import ConversationTurn

MAX_HISTORY_TURNS = 6     # hard cap (3 user + 3 assistant)
MAX_HISTORY_TOKENS = 800  # soft cap after hard cap

def trim_history(history: List[ConversationTurn]) -> List[ConversationTurn]:
    """
    Trims the conversation history to fit within turn and token limits.
    """
    if not history:
        return []

    # Hard cap: keep newest MAX_HISTORY_TURNS
    history = history[-MAX_HISTORY_TURNS:]
    
    # Soft cap: trim oldest until under budget, but always keep at least 1 exchange (2 turns) if possible
    while _estimate_tokens(history) > MAX_HISTORY_TOKENS:
        if len(history) <= 2:
            break
        history = history[1:]
        
    return history

def _estimate_tokens(history: List[ConversationTurn]) -> int:
    """
    Estimates the number of tokens in the history.
    Using a fast estimate of len(text.split()) * 1.3
    """
    if not history:
        return 0
    total_words = sum(len(t.content.split()) for t in history)
    return int(total_words * 1.3)

def build_effective_query(query: str, history: List[ConversationTurn]) -> str:
    """
    Augments the query with the last assistant response if the query is short,
    to improve retrieval relevance for follow-ups (e.g. resolving pronouns).
    """
    if history and len(query.split()) < 15:
        # Find the last assistant turn
        last_assistant = next(
            (t.content[-300:] for t in reversed(history) if t.role == 'assistant'),
            ""
        )
        if last_assistant:
            return f"{query} {last_assistant}".strip()
    return query
