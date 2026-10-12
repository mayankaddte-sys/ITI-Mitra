# ITI-Mitra: RAG chatbot for ITI trainees

Answers trainee questions on **admission, exams, scholarships, apprenticeship and jobs** strictly from the
documents your office uploads (PDF / DOCX / TXT). Hindi, English and Hinglish are supported.

## What is in this version
- **Student page** (`/`) – chat only. **Admin page** (`/admin.html`) – upload, list, delete; protected by `ADMIN_API_KEY`.
- Upload hardening: sanitised filenames, extension and size checks, no path traversal; frontend uses `textContent` (no XSS).
- No pickle: index is `store.json` + `embeddings.npy`. Re-uploading a file **replaces** it; single files can be deleted.
- Hindi-aware chunking (handles the danda `।`), overlap, page numbers in sources, optional document date/category.
- Relevance threshold: if nothing relevant is found the bot says so and shows the helpline text – the LLM is not called.
- Conversation memory (last turns, kept in the browser), higher answer length, batched embeddings, vectorised search.
- Per-IP rate limit on `/chat`, generic error messages (details only in the server log), CORS limited to configured origins.
- Optional OCR for scanned / legacy-font PDFs.
- **Feedback and gaps:** 👍/👎 under each answer, and an admin panel listing the questions the bot could not answer (grouped, with counts) and the answers marked 👎, so you know which documents to upload next. Phone/Aadhaar-like numbers and e-mails are masked before storing; no IP or user id is kept; rows are deleted after `RETENTION_DAYS` (default 90). Turn off with `LOG_QUESTIONS=false`.
- Tests: `pytest` (22 tests, no network or API key needed).

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # set OPENAI_API_KEY and ADMIN_API_KEY
uvicorn backend.app:app --reload --port 8000        # run from the project root
```
Open http://localhost:8000/ (students) and http://localhost:8000/admin.html (admin; paste your `ADMIN_API_KEY`).

Generate an admin key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### OCR (optional, for scanned PDFs)
```bash
sudo apt install tesseract-ocr tesseract-ocr-hin poppler-utils
pip install -r requirements-ocr.txt
```
Without OCR, scanned or legacy-font PDFs are rejected with a clear message instead of being indexed as garbage.

### Tests
```bash
pip install -r requirements-dev.txt && pytest
```

## API
Public: `GET /health`, `POST /chat` `{ "message": "...", "history": [{"role":"user|assistant","content":"..."}] }`

Admin (header `X-API-Key`): `GET /admin/files`, `POST /admin/upload` (form: `file`, optional `category`, `issue_date`),
`DELETE /admin/files/{filename}`, `DELETE /admin/knowledge-base`, `GET|DELETE /admin/insights`.
Public feedback: `POST /feedback` `{ "rating": "up|down", "question": "...", "reply": "...", "comment": "" }`.

## Deployment notes
- Use a **persistent disk/volume** for `vector_db/` and `uploads/` (free tiers that wipe the disk lose your index).
- Run **one worker** (the index and rate limiter live in process memory). For several workers use a shared vector DB and Redis.
- Put it behind HTTPS. Set `TRUST_PROXY=true` only if a trusted reverse proxy sets `X-Forwarded-For`.
- Docker: `docker build -t iti-mitra . && docker run -p 8000:8000 --env-file .env -v $PWD/data/vector_db:/app/vector_db -v $PWD/data/uploads:/app/uploads iti-mitra`

## Privacy
Questions and document text are sent to OpenAI to create embeddings and answers. Check this against your department's
data policy before going public, and keep personal data out of uploads. The server stores no chat history; it only keeps the masked unanswered-question / feedback log described above.

## Known limits / next steps
Metadata filters by category, WhatsApp/Telegram channel, voice input,
and a managed vector database (pgvector / Qdrant) for larger collections.
