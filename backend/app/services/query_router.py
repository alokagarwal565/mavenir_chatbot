"""
QueryRouter — deterministic-first query scope classifier.

Classification runs before any retrieval. The router:
  1. Guards against prompt injection (highest priority, non-bypassable)
  2. Detects social/greeting messages (fast path, no RAG cost)
  3. Detects capability/meta questions (fast path)
  4. Detects clearly out-of-scope requests (decline)
  5. Detects explicit 3GPP questions (full RAG pipeline)
  6. Uses conversation context to route ambiguous follow-ups
  7. Detects adjacent telecom questions (RAG with answerability gate)
  8. Falls back to clarification for truly ambiguous input

Returns a RoutingDecision with: category, route, confidence, reason, fast_response.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from app.services.fast_responses import (
    CAPABILITY_RESPONSE,
    CLARIFY_RESPONSE,
    DECLINE_RESPONSE,
    INJECTION_RESPONSE,
    get_greeting_response,
)

# ---------------------------------------------------------------------------
# Routing categories
# ---------------------------------------------------------------------------
CAT_GREETING    = "greeting"
CAT_CAPABILITY  = "capability"
CAT_FOLLOWUP    = "followup_3gpp"
CAT_3GPP        = "3gpp_direct"
CAT_TELECOM     = "adjacent_telecom"
CAT_AMBIGUOUS   = "ambiguous"
CAT_OUT_SCOPE   = "out_of_scope"
CAT_INJECTION   = "injection"

ROUTE_FAST      = "fast_path"
ROUTE_RAG       = "rag_pipeline"
ROUTE_DECLINE   = "decline"
ROUTE_CLARIFY   = "clarify"


@dataclass
class RoutingDecision:
    category: str
    route: str
    confidence: float
    reason: str
    fast_response: Optional[str] = None


# ---------------------------------------------------------------------------
# Pattern lists  (compiled once at import time)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = re.compile(
    r"""
    ignore\s+(your\s+|all\s+|previous\s+|these\s+)?instructions |    
    act\s+as\s+(a\s+|an\s+|my\s+)? |
    pretend\s+(you\s+are|to\s+be) |
    you\s+are\s+now |
    forget\s+(?:\w+\s+){0,3}instructions |
    \bDAN\b |
    jailbreak |
    do\s+anything\s+now |
    ignore\s+your\s+previous |
    new\s+persona |
    override\s+your\s+
    """,
    re.IGNORECASE | re.VERBOSE,
)

_GREETING_TOKENS = frozenset([
    "hi", "hello", "hey", "hiya", "howdy",
    "thanks", "thank", "ty", "thx", "cheers",
    "bye", "goodbye", "cya", "later", "see you",
    "ok", "okay", "k", "sure", "yep", "yes", "no", "nope",
    "great", "nice", "cool", "perfect", "awesome", "good",
    "got", "much", "very", "noted", "understood", "alright", "right",
    "hmm", "interesting", "wow",
])

_CAPABILITY_PHRASES = [
    r"what can you (do|help|assist)",
    r"what do you (do|know|cover|support)",
    r"help me with",
    r"your capabilities",
    r"what (specs|specifications|documents|standards) do you",
    r"tell me about yourself",
    r"what are you",
    r"how (can|do) you help",
    r"what('s| is) your (purpose|function|role)",
]
_CAPABILITY_RE = re.compile("|".join(_CAPABILITY_PHRASES), re.IGNORECASE)

# 3GPP explicit identifiers
_3GPP_EXPLICIT_RE = re.compile(
    r"""
    \b(TS|TR)\s*\d{2}\.\d{3}\b |          # TS 23.501 / TR 38.801
    \b(Rel|Release)\s*-?\s*1[5-9]\b |     # Rel-15 through Rel-19
    \b(Rel|Release)\s*-?\s*20\b |         # Rel-20
    \b(AMF|SMF|UPF|PCF|UDM|AUSF|NRF|NEF|NSSF|UDR|UDSF|SMSF|N3IWF|TNGF)\b |
    \b(gNB|ng-eNB|RAN|RRC|NAS|PDCP|SDAP|NGAP|N1|N2|N3|N4|N6|N7|N8|N10|N11|N14|N22)\b |
    \b(S-NSSAI|NSSAI|SUPI|SUCI|GUTI|IMSI|IMEISV|5G-GUTI)\b |
    \b(PDU\s+[Ss]ession|QoS\s+[Ff]low|QFI|5QI|AMBR|GBR|MBR)\b |
    \b(5GMM|5GSM|Registration\s+[Pp]rocedure|Deregistration)\b |
    \b3GPP\b |
    \b5GC\b | \b5GS\b |
    \bNGRAN\b | \bNG-RAN\b |
    \bSBA\b | \bSBI\b |
    \bUE\s+Context\b | \bAN\s+Release\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TELECOM_GENERAL_RE = re.compile(
    r"""
    \b5G\b | \bLTE\b | \b4G\b | \bNR\b |
    \b(base\s+station|cell\s+tower|spectrum|millimeter\s+wave|mmwave|beamforming)\b |
    \b(core\s+network|radio\s+access|network\s+slice|network\s+slicing)\b |
    \b(handover|handoff|mobility|bearer|tunnel)\b |
    \b(subscriber|SIM|eSIM|UICC|authentication|encryption)\b |
    \b(uplink|downlink|bandwidth|latency|throughput)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_OUT_OF_SCOPE_RE = re.compile(
    r"""
    \b(weather|forecast|temperature|rain|sunny|cloudy)\b |
    \b(cricket|football|soccer|basketball|sports|match|score|tournament)\b |
    \b(recipe|cook|bake|food|restaurant|meal)\b |
    \b(write\s+(me\s+)?(a\s+)?(python|java|code|script|program|function))\b |
    \b(capital\s+of|who\s+is\s+the\s+(president|prime\s+minister))\b |
    \b(joke|funny|meme|entertainment)\b |
    \b(resume|cv|cover\s+letter|job\s+application)\b |
    \b(travel|hotel|flight|book\s+a\s+trip)\b |
    \b(stock\s+price|bitcoin|cryptocurrency|investment)\b |
    \b(movie|film|series|episode|actor|actress)\b |
    \b(translate\s+to|what\s+does\s+.{1,20}\s+mean\s+in\s+(french|spanish|german|hindi|arabic|chinese))\b |
    \b(general\s+(ai|assistant)|chatgpt|gpt|claude)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Follow-up signals (only meaningful when in a 3GPP conversation)
_FOLLOWUP_SIGNALS_RE = re.compile(
    r"""
    ^(can\s+you\s+)?(explain|elaborate|clarify|simplify|summarize|expand|rephrase)\s+(that|it|this|further|more)? |
    ^what\s+did\s+you\s+mean |
    ^(how\s+is\s+that|how\s+does\s+that)\s+(related|connect) |
    ^(tell\s+me\s+more|more\s+details?|go\s+on|continue) |
    ^(what\s+about|how\s+about)\s+(the|that|this)?\s*\??\s*$ |
    ^(and|but|so|also|additionally|furthermore)\s |
    ^(what|how|why|when|where)\s+(is|are|was|were|does|did)\s+(that|it|this)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

class QueryRouter:

    @staticmethod
    def classify(
        query: str,
        conversation_history: Optional[List] = None,
    ) -> RoutingDecision:
        """
        Classify the query and return a RoutingDecision.
        conversation_history: list of ConversationTurn (or dicts with role/content).
        """
        q = query.strip()
        q_lower = q.lower()

        # ------------------------------------------------------------------
        # 1. Injection guard — highest priority, non-bypassable
        # ------------------------------------------------------------------
        if _INJECTION_PATTERNS.search(q):
            return RoutingDecision(
                category=CAT_INJECTION,
                route=ROUTE_DECLINE,
                confidence=1.0,
                reason="Prompt injection attempt detected",
                fast_response=INJECTION_RESPONSE,
            )

        # ------------------------------------------------------------------
        # 2. Out-of-scope block-list — runs before context check to prevent
        #    context laundering (3GPP history ≠ permission for general Qs)
        # ------------------------------------------------------------------
        if _OUT_OF_SCOPE_RE.search(q):
            return RoutingDecision(
                category=CAT_OUT_SCOPE,
                route=ROUTE_DECLINE,
                confidence=0.95,
                reason="Query matched out-of-scope topic block-list",
                fast_response=DECLINE_RESPONSE,
            )

        # ------------------------------------------------------------------
        # 3. Capability / meta questions
        # ------------------------------------------------------------------
        if _CAPABILITY_RE.search(q):
            return RoutingDecision(
                category=CAT_CAPABILITY,
                route=ROUTE_FAST,
                confidence=0.95,
                reason="Capability question detected",
                fast_response=CAPABILITY_RESPONSE,
            )

        # ------------------------------------------------------------------
        # 4. Explicit 3GPP identifiers → always RAG
        # ------------------------------------------------------------------
        if _3GPP_EXPLICIT_RE.search(q):
            return RoutingDecision(
                category=CAT_3GPP,
                route=ROUTE_RAG,
                confidence=0.95,
                reason="Explicit 3GPP identifier found in query",
            )

        # ------------------------------------------------------------------
        # 5. Social / greeting detection
        #    Only for short messages with no telecom signal
        # ------------------------------------------------------------------
        tokens = re.findall(r"[a-z']+", q_lower)
        is_short = len(tokens) <= 5
        has_telecom = bool(_TELECOM_GENERAL_RE.search(q))

        if is_short and not has_telecom:
            token_set = set(tokens)
            # Check if all meaningful tokens are greeting tokens
            meaningful = token_set - {"i", "a", "the", "to", "is", "it", "me", "my", "you", "your"}
            if meaningful and meaningful.issubset(_GREETING_TOKENS):
                return RoutingDecision(
                    category=CAT_GREETING,
                    route=ROUTE_FAST,
                    confidence=0.92,
                    reason="Social/greeting message detected",
                    fast_response=get_greeting_response(q),
                )

        # ------------------------------------------------------------------
        # 6. Conversation context check for ambiguous follow-ups
        # ------------------------------------------------------------------
        last_3gpp_in_context = _last_turn_was_3gpp(conversation_history)

        if _FOLLOWUP_SIGNALS_RE.search(q):
            if last_3gpp_in_context:
                return RoutingDecision(
                    category=CAT_FOLLOWUP,
                    route=ROUTE_RAG,
                    confidence=0.85,
                    reason="Follow-up signal in active 3GPP conversation",
                )
            # Follow-up but no 3GPP context → clarify
            return RoutingDecision(
                category=CAT_AMBIGUOUS,
                route=ROUTE_CLARIFY,
                confidence=0.70,
                reason="Follow-up signal but no active 3GPP context",
                fast_response=CLARIFY_RESPONSE,
            )

        # ------------------------------------------------------------------
        # 7. Adjacent telecom (general) → RAG with answerability gate
        # ------------------------------------------------------------------
        if has_telecom:
            return RoutingDecision(
                category=CAT_TELECOM,
                route=ROUTE_RAG,
                confidence=0.75,
                reason="General telecom keyword present; routing to RAG with answerability gate",
            )

        # ------------------------------------------------------------------
        # 8. Short message in active 3GPP context → treat as follow-up
        # ------------------------------------------------------------------
        if is_short and last_3gpp_in_context:
            return RoutingDecision(
                category=CAT_FOLLOWUP,
                route=ROUTE_RAG,
                confidence=0.70,
                reason="Short message in active 3GPP conversation context",
            )

        # ------------------------------------------------------------------
        # 9. Default: ask for clarification
        # ------------------------------------------------------------------
        return RoutingDecision(
            category=CAT_AMBIGUOUS,
            route=ROUTE_CLARIFY,
            confidence=0.55,
            reason="Insufficient signal for routing; requesting clarification",
            fast_response=CLARIFY_RESPONSE,
        )


def _last_turn_was_3gpp(history) -> bool:
    """
    Returns True if any of the last 3 assistant turns contain 3GPP content.
    Accepts list of ConversationTurn objects or dicts.
    """
    if not history:
        return False
    assistant_turns = [
        t for t in history
        if (getattr(t, "role", None) or t.get("role", "")) == "assistant"
    ]
    for turn in assistant_turns[-3:]:
        content = getattr(turn, "content", None) or turn.get("content", "")
        if _3GPP_EXPLICIT_RE.search(content) or _TELECOM_GENERAL_RE.search(content):
            return True
    return False
