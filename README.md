# ITI-Mitra: RAG-Enabled AI Chatbot

ITI-Mitra is a powerful Retrieval-Augmented Generation (RAG) chatbot designed specifically for ITI trainees. It helps with:

- **Admission Information** - Application procedures, eligibility criteria, course details
- **Examination Guidance** - Exam preparation, schedules, exam formats
- **Scholarship Help** - Available scholarships, eligibility, application process
- **Apprenticeship Support** - How to apply, benefits, industry opportunities
- **Job Opportunities** - Career paths, job search strategies, placement assistance

## Key Features

✅ **RAG-Enabled**: Upload PDF, DOCX, and TXT documents - the system automatically indexes them
✅ **No Login Required**: Open access for all ITI trainees
✅ **Smart Search**: Uses OpenAI embeddings to find relevant information
✅ **Source Attribution**: Shows which documents provided the answer
✅ **Real-time Upload**: Add or remove knowledge base documents anytime
✅ **Clean UI**: Intuitive interface for easy interaction

## Tech Stack

**Backend:**
- FastAPI
- OpenAI API (embeddings & GPT)
- Vector Store (disk-based with pickle)
- File Processing (PDF, DOCX, TXT)

**Frontend:**
- HTML5 / CSS3
- Vanilla JavaScript
- Responsive Design

## Setup & Installation

### 1. Clone the repository
```bash
git clone <repo-url>
cd ITI-Mitra
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```env
OPENAI_API_KEY=sk-your-actual-key
OPENAI_MODEL=gpt-4o-mini
VECTOR_DB_PATH=./vector_db
UPLOAD_DIR=./uploads
```

### 5. Start the backend
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open the frontend

Option A: Open `frontend/index.html` directly in your browser

Option B: Serve locally
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

## Usage

1. **Upload Documents**: Drag and drop PDF/DOCX/TXT files in the sidebar
2. **Wait for Indexing**: The system will automatically process and index the documents
3. **Ask Questions**: Type your question in the chat box
4. **Get Answers**: The chatbot retrieves relevant information and provides answers with source attribution

## API Endpoints

### Health Check
```bash
GET /health
```
Returns the status and vector DB statistics.

### Upload File
```bash
POST /upload
Content-Type: multipart/form-data

Body:
- file: <binary file content>
```

### Chat
```bash
POST /chat
Content-Type: application/json

Body:
{
  "message": "Your question here"
}
```

Response:
```json
{
  "reply": "Answer from the chatbot",
  "sources": ["document1.pdf", "document2.docx"]
}
```

### Get Knowledge Base Stats
```bash
GET /knowledge-base
```

### Get Indexed Files
```bash
GET /files-indexed
```

### Clear Knowledge Base
```bash
DELETE /knowledge-base
```

## File Support

- **PDF** (.pdf) - Text extraction from all pages
- **Word Documents** (.docx) - Text and table extraction
- **Text Files** (.txt) - Plain text files

## Example Workflow

1. Admin uploads `admission_guide.pdf`, `scholarship_info.docx`, `job_placements.txt`
2. Student asks: "What are the eligibility criteria for ITI admission?"
3. Chatbot searches the vector database for relevant chunks
4. Responds with information from `admission_guide.pdf`
5. Shows source: "📄 admission_guide.pdf"

## Performance

- **Embedding Model**: text-embedding-3-small (fast & cost-effective)
- **LLM**: gpt-4o-mini (fast responses, lower cost)
- **Storage**: Disk-based vector store (persists between sessions)
- **Latency**: ~1-2 seconds per query

## Security & Privacy

- No user login/authentication (open access)
- Documents stored locally in `./uploads` and `./vector_db`
- API keys stored in `.env` (not committed to git)
- No user data is tracked or logged

## Troubleshooting

### Issue: "Connection error"
**Solution**: Ensure backend is running on `http://localhost:8000`

### Issue: "No documents indexed"
**Solution**: Upload documents using the sidebar file uploader

### Issue: "OpenAI API error"
**Solution**: Check if your API key is valid and has sufficient credits

### Issue: "File upload fails"
**Solution**: Ensure file is supported (.pdf, .docx, .txt) and not corrupted

## Deployment

### Option 1: Render + Vercel

**Backend on Render:**
1. Push to GitHub
2. Create new Web Service on Render
3. Set `python -m uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
4. Set environment variables

**Frontend on Vercel:**
1. Set `API_URL` environment variable in frontend/script.js
2. Deploy to Vercel

### Option 2: Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Future Enhancements

- [ ] Multi-language support (Hindi, Tamil, etc.)
- [ ] Chat history persistence
- [ ] Admin panel for document management
- [ ] Advanced search filters
- [ ] Integration with state ITI databases
- [ ] Mobile app version
- [ ] Analytics and usage tracking

## License

MIT License - Feel free to use and modify

## Support

For issues or feature requests, open a GitHub issue or contact the maintainers.

---

**Made with ❤️ for ITI Trainees**
