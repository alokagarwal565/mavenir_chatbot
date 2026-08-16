# Mavenir 3GPP Standards Intelligence Assistant

Authoritative 3GPP 5GS Standards RAG Assistant (Release 17 & 18 Architecture, Procedures, NAS Signaling, Security, SBI APIs, and NR RRC/NGAP).

## Production Architecture (100% Free Tier Stack)
- **Backend API:** FastAPI on Render (Free Tier Web Service)
- **Database & Vectors:** Neon PostgreSQL + pgvector (0.5 GB Free Tier)
- **Frontend UI:** React 18 + Vite + TypeScript on Vercel
- **LLM Grounding:** Gemini 3.5 Flash Lite with 3-Key Failover Cascade Pool
- **Embeddings:** BAAI/bge-m3 (1024-dim dense vectors) + BGE Reranker

## Getting Started

1. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Add your Neon DATABASE_URL and GEMINI_API_KEYs
   ```

2. **Run Tests:**
   ```bash
   pytest backend/tests/unit backend/tests/adversarial
   ```

3. **Start Backend Locally:**
   ```bash
   uvicorn app.main:app --app-dir backend --port 7860 --reload
   ```

4. **Start Frontend:**
   ```bash
   cd frontend && npm install && npm run dev
   ```
