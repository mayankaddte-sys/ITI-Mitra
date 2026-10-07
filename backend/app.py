import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from vector_store import VectorStore
from file_processor import FileProcessor

load_dotenv()

app = FastAPI(title="ITI-Mitra RAG Chatbot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

vector_store = VectorStore()

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
async def health():
    stats = vector_store.get_stats()
    return {"status": "ok", "vector_db": stats}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        with open(file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        text = FileProcessor.process_file(file_path)
        
        if not text.strip():
            raise Exception("File is empty or unreadable")
        
        vector_store.add_text(text, metadata={
            "filename": file.filename,
            "file_type": os.path.splitext(file.filename)[1]
        })
        
        stats = vector_store.get_stats()
        return {
            "status": "success",
            "filename": file.filename,
            "message": f"File uploaded and indexed successfully",
            "vector_db": stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.message.strip()
    if not user_message:
        return {"reply": "Please type your question."}

    search_results = vector_store.search(user_message, top_k=3)
    
    if not search_results:
        return {
            "reply": "I don't have any documents indexed yet. Please upload documents to the knowledge base.",
            "sources": []
        }
    
    context = "\n\n".join([chunk for chunk, _, _ in search_results])
    sources = [metadata["filename"] for _, metadata, _ in search_results]

    system_prompt = """
You are ITI-Mitra, a helpful chatbot for ITI trainees.
Answer using only the provided context from the uploaded documents.
If the answer is not available in the context, say you do not have enough information.
Keep answers simple, clear, and friendly.
Be concise and helpful.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{user_message}"}
            ],
            temperature=0.2,
            max_tokens=300
        )
        
        answer = response.choices[0].message.content.strip()
        return {
            "reply": answer,
            "sources": list(set(sources))
        }
    except Exception as e:
        return {"reply": f"Error processing your question: {str(e)}", "sources": []}

@app.get("/knowledge-base")
async def get_knowledge_base_info():
    return vector_store.get_stats()

@app.delete("/knowledge-base")
async def clear_knowledge_base():
    vector_store.clear()
    return {"status": "success", "message": "Knowledge base cleared"}

@app.get("/files-indexed")
async def get_indexed_files():
    files = set([m.get("filename") for m in vector_store.metadata])
    return {"files": list(files), "count": len(files)}
