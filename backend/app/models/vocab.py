import re

# Layer 3: Network Functions Vocabulary
NF_VOCAB = {
    "amf": re.compile(r'\b(AMF|Access and Mobility Management Function)\b', re.IGNORECASE),
    "smf": re.compile(r'\b(SMF|Session Management Function)\b', re.IGNORECASE),
    "upf": re.compile(r'\b(UPF|User Plane Function)\b', re.IGNORECASE),
    "udm": re.compile(r'\b(UDM|Unified Data Management)\b', re.IGNORECASE),
    "ausf": re.compile(r'\b(AUSF|Authentication Server Function)\b', re.IGNORECASE),
    "nssf": re.compile(r'\b(NSSF|Network Slice Selection Function)\b', re.IGNORECASE),
    "pcf": re.compile(r'\b(PCF|Policy Control Function)\b', re.IGNORECASE),
    "nef": re.compile(r'\b(NEF|Network Exposure Function)\b', re.IGNORECASE),
    "nrf": re.compile(r'\b(NRF|Network Function Repository Function)\b', re.IGNORECASE),
    "gnb": re.compile(r'\b(gNB|NG-RAN node|base station)\b', re.IGNORECASE),
    "ue": re.compile(r'\b(UE|User Equipment)\b', re.IGNORECASE),
    "rrc": re.compile(r'\b(RRC|Radio Resource Control)\b', re.IGNORECASE),
    "nas": re.compile(r'\b(NAS|Non-Access-Stratum)\b', re.IGNORECASE),
    "ngap": re.compile(r'\b(NGAP|NG Application Protocol)\b', re.IGNORECASE),
}

# Layer 2: Procedures & Functional Topics
PROC_VOCAB = {
    "proc:registration": re.compile(r'\b(registration|initial registration|mobility registration|periodic registration)\b', re.IGNORECASE),
    "proc:pdu_session": re.compile(r'\b(PDU session|session establishment|session modification|session release)\b', re.IGNORECASE),
    "proc:handover": re.compile(r'\b(handover|Xn handover|N2 handover|intra-system handover)\b', re.IGNORECASE),
    "proc:aka_auth": re.compile(r'\b(5G AKA|EAP-AKA|authentication vector|SUCI|SUPI|primary authentication)\b', re.IGNORECASE),
    "proc:service_request": re.compile(r'\b(service request|UE-triggered service request)\b', re.IGNORECASE),
    "proc:deregistration": re.compile(r'\b(deregistration|explicit deregistration)\b', re.IGNORECASE),
    "topic:slicing": re.compile(r'\b(network slice|network slicing|S-NSSAI|NSSAI|SST|SD)\b', re.IGNORECASE),
    "topic:qos": re.compile(r'\b(QoS flow|5QI|QFI|guaranteed bit rate|GBR|Non-GBR)\b', re.IGNORECASE),
    "topic:timers": re.compile(r'\b(T3512|T3502|T3510|T3520|timer)\b', re.IGNORECASE),
}

# Layer 4: Interfaces & Reference Points
IFACE_VOCAB = {
    "iface:n1": re.compile(r'\b(N1 reference point|N1 mode|over N1)\b', re.IGNORECASE),
    "iface:n2": re.compile(r'\b(N2 interface|N2 reference point|over N2)\b', re.IGNORECASE),
    "iface:n3": re.compile(r'\b(N3 interface|N3 reference point|over N3)\b', re.IGNORECASE),
    "iface:n4": re.compile(r'\b(N4 interface|N4 reference point|over N4|PFCP)\b', re.IGNORECASE),
    "iface:n6": re.compile(r'\b(N6 interface|Data Network interface)\b', re.IGNORECASE),
    "iface:n11": re.compile(r'\b(N11 interface|N11 reference point)\b', re.IGNORECASE),
    "iface:namf": re.compile(r'\b(Namf|Namf_Communication|Namf_EventExposure)\b', re.IGNORECASE),
    "iface:nsmf": re.compile(r'\b(Nsmf|Nsmf_PDUSession|Nsmf_EventExposure)\b', re.IGNORECASE),
    "iface:nudm": re.compile(r'\b(Nudm|Nudm_UECM|Nudm_SDM)\b', re.IGNORECASE),
    "iface:nnrf": re.compile(r'\b(Nnrf|Nnrf_NFDiscovery|Nnrf_NFManagement)\b', re.IGNORECASE),
    "iface:xn": re.compile(r'\b(Xn interface|Xn-C|Xn-U)\b', re.IGNORECASE),
}

# Layer 5: Protocol / Serialization
PROTO_VOCAB = {
    "proto:nas_5gmm": re.compile(r'\b(5GMM|5GS Mobility Management)\b', re.IGNORECASE),
    "proto:nas_5gsm": re.compile(r'\b(5GSM|5GS Session Management)\b', re.IGNORECASE),
    "proto:ngap": re.compile(r'\b(NGAP|NG Application Protocol|38\.413)\b', re.IGNORECASE),
    "proto:rrc": re.compile(r'\b(RRC|RRCSetup|RRCReconfiguration|38\.331)\b', re.IGNORECASE),
    "proto:http2_json": re.compile(r'\b(HTTP/2|application/json|RESTful|SBI)\b', re.IGNORECASE),
    "proto:pfcp": re.compile(r'\b(PFCP|Packet Forwarding Control Protocol|29\.244)\b', re.IGNORECASE),
}
