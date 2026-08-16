"""
Pre-computed fast-path responses for non-RAG query categories.
These are returned instantly without touching the retrieval pipeline.
"""
import random

CAPABILITY_RESPONSE = (
    "I'm a **3GPP Standards Intelligence Assistant**. Here's what I can help with:\n\n"
    "- Technical questions about 3GPP specifications (TS/TR documents)\n"
    "- 5G Core network functions: AMF, SMF, UPF, PCF, UDM, AUSF, NRF, NEF, NSSF\n"
    "- Procedures: registration, PDU session establishment, authentication, handover\n"
    "- NAS, RRC, PDCP, SDAP protocol details\n"
    "- QoS, network slicing, S-NSSAI, policy frameworks\n"
    "- Clause-level citations from indexed 3GPP specifications\n\n"
    "I cannot help with general knowledge, coding tasks, weather, or topics outside "
    "3GPP and telecommunications standards."
)

GREETING_RESPONSES = [
    "Hello! Ask me anything about 3GPP 5G standards.",
    "Hi there! I'm ready to help with 3GPP technical questions.",
    "Hey! What 3GPP specification can I help you with today?",
    "Hello! Feel free to ask about any 3GPP procedure, specification, or network function.",
]

THANKS_RESPONSES = [
    "You're welcome! Let me know if you have more 3GPP questions.",
    "Happy to help! Feel free to ask anything else about the standards.",
    "Glad that helped! Any other 3GPP topics you'd like to explore?",
]

FAREWELL_RESPONSES = [
    "Goodbye! Come back anytime for 3GPP standards help.",
    "See you! Feel free to return with any 3GPP questions.",
    "Take care! I'll be here whenever you need standards assistance.",
]

DECLINE_RESPONSE = (
    "That's outside my scope. I specialize in **3GPP telecommunications standards**. "
    "Try asking about a specific TS document, a network function procedure, "
    "or a 5G architecture topic."
)

INJECTION_RESPONSE = (
    "I can only assist with 3GPP technical standards. "
    "Let me know if you have a question about a specification."
)

CLARIFY_RESPONSE = (
    "Could you clarify your question? I'm best equipped to help with specific "
    "3GPP topics — for example, a particular specification (like TS 23.502), "
    "a network function (like AMF or SMF), or a procedure (like PDU session establishment)."
)


def get_greeting_response(text: str) -> str:
    """Pick appropriate greeting response based on input."""
    t = text.lower().strip().rstrip("!.,")
    if any(w in t for w in ("thank", "thanks", "thx", "ty")):
        return random.choice(THANKS_RESPONSES)
    if any(w in t for w in ("bye", "goodbye", "see you", "cya", "later")):
        return random.choice(FAREWELL_RESPONSES)
    return random.choice(GREETING_RESPONSES)
