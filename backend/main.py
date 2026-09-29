import os
import time
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from pypdf import PdfReader


# =========================================================
# Environment
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

EMBEDDING_MODEL = "gemini-embedding-2"


if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing in .env"
    )


# =========================================================
# Gemini Client
# =========================================================

client = genai.Client(
    api_key=API_KEY
)


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="Akhil AI Chatbot"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Persistent Multi-Document PDF Knowledge Base
# =========================================================

DOCUMENT_STORE_FILE = BASE_DIR / "document_store.json"

pdf_chunks = []
pdf_documents = {}


def save_document_store():
    """Save all PDF metadata, chunks, and embeddings to disk."""

    try:
        serializable_chunks = []

        for chunk in pdf_chunks:
            serializable_chunks.append({
                "id": chunk["id"],
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "page": chunk.get("page"),
                "text": chunk["text"],
                "embedding": chunk["embedding"].tolist()
            })

        store = {
            "documents": list(pdf_documents.values()),
            "chunks": serializable_chunks
        }

        with open(
            DOCUMENT_STORE_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                store,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:
        print("Document store save error:", e)


def load_document_store():
    """Load saved PDF documents, chunks, and embeddings at startup."""

    global pdf_chunks
    global pdf_documents

    if not DOCUMENT_STORE_FILE.exists():
        return

    try:
        with open(
            DOCUMENT_STORE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            store = json.load(file)

        pdf_documents = {
            item["document_id"]: item
            for item in store.get("documents", [])
        }

        loaded_chunks = []

        for item in store.get("chunks", []):
            embedding = np.array(
                item.get("embedding", []),
                dtype=np.float32
            )

            if embedding.size == 0:
                continue

            loaded_chunks.append({
                "id": item["id"],
                "document_id": item["document_id"],
                "filename": item["filename"],
                "page": item.get("page"),
                "text": item["text"],
                "embedding": embedding
            })

        pdf_chunks = loaded_chunks

        print(
            f"PDF knowledge loaded: "
            f"{len(pdf_documents)} documents, "
            f"{len(pdf_chunks)} chunks"
        )

    except Exception as e:
        print("Document store load error:", e)
        pdf_chunks = []
        pdf_documents = {}


load_document_store()

# =========================================================
# Long-Term Memory
# =========================================================

MEMORY_FILE = BASE_DIR / "memory.json"


def load_memory():

    if not MEMORY_FILE.exists():

        return {
            "facts": []
        }

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            "Memory load error:",
            e
        )

        return {
            "facts": []
        }


def save_memory(memory):

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                memory,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            "Memory save error:",
            e
        )


# Load memory when backend starts
LONG_TERM_MEMORY = load_memory()


print(
    f"Long-term memory loaded: "
    f"{len(LONG_TERM_MEMORY.get('facts', []))} facts"
)
# ============================================================
# AUTOMATIC LONG-TERM MEMORY
# ============================================================

def remember_fact(key, value):
    """
    Save or update a personal fact in memory.json.
    """

    global LONG_TERM_MEMORY

    facts = LONG_TERM_MEMORY.setdefault("facts", [])

    # Check if this key already exists
    for fact in facts:
        if fact.get("key") == key:
            fact["value"] = value
            save_memory(LONG_TERM_MEMORY)
            return

    # Add new fact
    facts.append({
        "key": key,
        "value": value
    })

    save_memory(LONG_TERM_MEMORY)

    print(f"Memory saved: {key} = {value}")


def extract_memory_from_message(message):
    """
    Detect simple personal facts from the user's message.
    """

    import re

    text = message.strip()

    # --------------------------------------------------------
    # My name is ...
    # --------------------------------------------------------

    match = re.search(
        r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{1,50})",
        text,
        re.IGNORECASE
    )

    if match:
        name = match.group(1).strip()

        # Remove common trailing phrases
        name = re.split(
            r"\b(and|but|i|my)\b",
            name,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0].strip()

        if name:
            remember_fact("name", name)

    # --------------------------------------------------------
    # I am learning ...
    # --------------------------------------------------------

    match = re.search(
        r"\b(?:i am|i'm)\s+learning\s+(.+?)(?:[.!?]|$)",
        text,
        re.IGNORECASE
    )

    if match:
        subject = match.group(1).strip()

        if subject:
            remember_fact("learning", subject)

    # --------------------------------------------------------
    # My project is ...
    # --------------------------------------------------------

    match = re.search(
        r"\bmy project is\s+(.+?)(?:[.!?]|$)",
        text,
        re.IGNORECASE
    )

    if match:
        project = match.group(1).strip()

        if project:
            remember_fact("project", project)

    # --------------------------------------------------------
    # I work on ...
    # --------------------------------------------------------

    match = re.search(
        r"\bi work on\s+(.+?)(?:[.!?]|$)",
        text,
        re.IGNORECASE
    )

    if match:
        work = match.group(1).strip()

        if work:
            remember_fact("work", work)


def get_memory_text():
    """
    Convert saved memory facts into text for the AI.
    """

    facts = LONG_TERM_MEMORY.get("facts", [])

    if not facts:
        return "No long-term memory is available."

    memory_lines = []

    for fact in facts:
        key = fact.get("key", "")
        value = fact.get("value", "")

        memory_lines.append(
            f"{key}: {value}"
        )

    return "\n".join(memory_lines)
# =========================================================
# Akhil Personal Knowledge Base
# =========================================================

KNOWLEDGE_DIR = BASE_DIR / "akhil_knowledge"


def load_akhil_knowledge():

    knowledge = []

    if not KNOWLEDGE_DIR.exists():

        print(
            "Akhil knowledge folder not found."
        )

        return ""


    for file_path in KNOWLEDGE_DIR.glob("*.txt"):

        try:

            content = file_path.read_text(
                encoding="utf-8"
            )

            if content.strip():

                knowledge.append(
                    f"""
SOURCE: {file_path.name}

{content}
"""
                )

        except Exception as e:

            print(
                f"Knowledge file error: "
                f"{file_path.name} - {e}"
            )


    return "\n\n".join(
        knowledge
    )


AKHIL_KNOWLEDGE = load_akhil_knowledge()


print(
    f"Akhil knowledge loaded: "
    f"{len(AKHIL_KNOWLEDGE)} characters"
)


# =========================================================
# Request Models
# =========================================================

class ChatRequest(BaseModel):

    message: str

    history: list = []


class PDFQuestionRequest(BaseModel):

    question: str

    top_k: int = 5


class AkhilQuestionRequest(BaseModel):

    question: str


# =========================================================
# Home
# =========================================================

@app.get("/")
def home():

    return {

        "message": "Akhil AI Backend is running!",

        "model": MODEL,

        "pdf_chunks": len(pdf_chunks),

        "pdf_documents": len(pdf_documents),

        "akhil_knowledge": bool(
            AKHIL_KNOWLEDGE.strip()
        )

    }


# =========================================================
# Text Chunking
# =========================================================

def split_text(
    text,
    chunk_size=800,
    overlap=100
):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[
            start:end
        ].strip()

        if chunk:

            chunks.append(
                chunk
            )

        start += (
            chunk_size - overlap
        )


    return chunks


# =========================================================
# Create Embedding
# =========================================================

def create_embedding(text):

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return np.array(
        result.embeddings[0].values,
        dtype=np.float32
    )


def create_embeddings_batch(texts, max_retries=3, base_delay=2):

    """
    Create embeddings for multiple texts in one API request.

    This is much faster than making one API request per chunk.
    """

    if not texts:
        return []

    for attempt in range(max_retries):

        try:

            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts
            )

            embeddings = []

            for item in result.embeddings:

                embeddings.append(
                    np.array(
                        item.values,
                        dtype=np.float32
                    )
                )

            if len(embeddings) != len(texts):
                raise ValueError(
                    "Embedding count does not match input text count."
                )

            return embeddings

        except Exception as e:

            error_text = str(e)

            # Retry temporary API/rate-limit errors
            retryable = (
                "429" in error_text
                or
                "500" in error_text
                or
                "502" in error_text
                or
                "503" in error_text
                or
                "UNAVAILABLE" in error_text
                or
                "RESOURCE_EXHAUSTED" in error_text
            )

            if not retryable:
                raise

            if attempt < max_retries - 1:

                delay = base_delay * (2 ** attempt)

                print(
                    f"Embedding service temporarily unavailable "
                    f"(attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {delay} seconds..."
                )

                time.sleep(delay)

            else:
                raise

    return []


# =========================================================
# Cosine Similarity
# =========================================================

def cosine_similarity(
    vector_a,
    vector_b
):

    denominator = (

        np.linalg.norm(vector_a)

        *

        np.linalg.norm(vector_b)

    )


    if denominator == 0:

        return 0.0


    return float(

        np.dot(
            vector_a,
            vector_b
        )

        /

        denominator

    )


# =========================================================
# Gemini Generate Content With Retry
# =========================================================

def generate_with_retry(
    contents,
    max_retries=3,
    base_delay=3
):

    """
    Retry Gemini generation when
    temporary 503 / UNAVAILABLE errors occur.

    Retry delays:
    3 seconds
    6 seconds
    final attempt
    """

    for attempt in range(
        max_retries
    ):

        try:

            return client.models.generate_content(

                model=MODEL,

                contents=contents

            )


        except Exception as e:

            error_text = str(e)


            # Retry only temporary errors

            if (
                "503" not in error_text
                and
                "UNAVAILABLE" not in error_text
            ):

                raise


            if attempt < max_retries - 1:

                delay = (
                    base_delay
                    *
                    (2 ** attempt)
                )


                print(

                    f"Gemini temporarily unavailable "

                    f"(attempt "
                    f"{attempt + 1}/"
                    f"{max_retries}). "

                    f"Retrying in "
                    f"{delay} seconds..."

                )


                time.sleep(
                    delay
                )


            else:

                raise


# =========================================================
# Normal Chat
# =========================================================

@app.post("/chat")
def chat(
    request: ChatRequest
):

    try:

        contents = []
        # Save important personal information permanently
        extract_memory_from_message(request.message)
        # Add long-term memory to the AI context
        memory_text = get_memory_text()

        contents.append({
            "role": "user",
            "parts": [{
                "text": f"""
        You have access to the user's long-term memory.

        Use this information only when it is relevant to the user's question.

        Long-term memory:
        {memory_text}
        """
            }]
        })

        contents.append({
            "role": "model",
            "parts": [{
                "text": "Understood. I will use the long-term memory when relevant."
            }]
        })
        
        recent_history = request.history[-20:]

        for item in recent_history:

            role = item.get(
                "role"
            )

            text = item.get(
                "content",
                ""
            )

            if role == "user":

                contents.append({

                    "role": "user",

                    "parts": [
                        {
                            "text": text
                        }
                    ]

                })

            elif role == "assistant":

                contents.append({

                    "role": "model",

                    "parts": [
                        {
                            "text": text
                        }
                    ]

                })


        # -------------------------------------------------
        # Add current user message
        # -------------------------------------------------

        contents.append({

            "role": "user",

            "parts": [
                {
                    "text": request.message
                }
            ]

        })


        # -------------------------------------------------
        # Gemini
        # -------------------------------------------------

        response = generate_with_retry(
            contents
        )


        return {

            "success": True,

            "answer": response.text

        }


    except Exception as e:

        print(
            "========== GEMINI ERROR =========="
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "==================================="
        )


        return {

            "success": False,

            "answer":
                f"API Error: {str(e)}"

        }

# =========================================================
# PDF Upload + RAG Indexing
# =========================================================

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):

    try:

        upload_started_at = time.time()

        # -------------------------------------------------
        # Validate PDF
        # -------------------------------------------------

        if file.content_type != "application/pdf":
            return {
                "success": False,
                "message": "Please upload a PDF file."
            }

        # -------------------------------------------------
        # Read uploaded PDF
        # -------------------------------------------------

        pdf_bytes = await file.read()

        if not pdf_bytes:
            return {
                "success": False,
                "message": "The uploaded PDF is empty."
            }

        # -------------------------------------------------
        # Create a stable document ID from file contents
        # -------------------------------------------------

        file_hash = hashlib.sha256(
            pdf_bytes
        ).hexdigest()

        document_id = file_hash[:16]

        # -------------------------------------------------
        # Duplicate protection
        # -------------------------------------------------

        if document_id in pdf_documents:
            existing = pdf_documents[document_id]

            return {
                "success": True,
                "duplicate": True,
                "document_id": document_id,
                "filename": existing["filename"],
                "pages": existing["pages"],
                "chunk_count": existing["chunk_count"],
                "total_documents": len(pdf_documents),
                "total_chunks": len(pdf_chunks),
                "message": "This PDF is already uploaded and indexed."
            }

        # -------------------------------------------------
        # Temporary PDF
        # -------------------------------------------------

        temp_pdf = BASE_DIR / f"temp_{document_id}.pdf"

        with open(
            temp_pdf,
            "wb"
        ) as f:
            f.write(pdf_bytes)

        try:

            # -------------------------------------------------
            # Read PDF
            # -------------------------------------------------

            reader = PdfReader(
                str(temp_pdf)
            )

            page_texts = []

            for page_number, page in enumerate(
                reader.pages,
                start=1
            ):

                page_text = page.extract_text() or ""

                if page_text.strip():
                    page_texts.append({
                        "page": page_number,
                        "text": page_text.strip()
                    })

        finally:

            # Always remove temporary PDF
            temp_pdf.unlink(
                missing_ok=True
            )

        # -------------------------------------------------
        # Check extracted text
        # -------------------------------------------------

        if not page_texts:
            return {
                "success": False,
                "message": "No readable text found in the PDF."
            }

        # -------------------------------------------------
        # Create chunks while preserving page numbers
        # -------------------------------------------------

        document_chunks = []

        for page_item in page_texts:

            page_chunks = split_text(
                page_item["text"],
                chunk_size=800,
                overlap=100
            )

            for chunk in page_chunks:
                document_chunks.append({
                    "page": page_item["page"],
                    "text": chunk
                })

        if not document_chunks:
            return {
                "success": False,
                "message": "No usable text chunks were created."
            }

        # -------------------------------------------------
        # Generate embeddings in batches
        # -------------------------------------------------

        new_chunks = []

        # Sending several chunks in one embedding request
        # is much faster than one API request per chunk.
        EMBEDDING_BATCH_SIZE = 10

        total_chunks = len(document_chunks)

        for batch_start in range(
            0,
            total_chunks,
            EMBEDDING_BATCH_SIZE
        ):

            batch_items = document_chunks[
                batch_start:
                batch_start + EMBEDDING_BATCH_SIZE
            ]

            batch_texts = [
                item["text"]
                for item in batch_items
            ]

            batch_number = (
                batch_start // EMBEDDING_BATCH_SIZE
            ) + 1

            total_batches = (
                (total_chunks + EMBEDDING_BATCH_SIZE - 1)
                // EMBEDDING_BATCH_SIZE
            )

            print(
                f"Creating embeddings batch "
                f"{batch_number}/{total_batches} "
                f"({batch_start + 1}-"
                f"{min(batch_start + len(batch_items), total_chunks)}/"
                f"{total_chunks}) "
                f"for {file.filename}"
            )

            embeddings = create_embeddings_batch(
                batch_texts
            )

            for offset, (
                chunk_item,
                embedding
            ) in enumerate(
                zip(batch_items, embeddings)
            ):

                index = batch_start + offset

                new_chunks.append({
                    "id": f"{document_id}_{index}",
                    "document_id": document_id,
                    "filename": file.filename,
                    "page": chunk_item["page"],
                    "text": chunk_item["text"],
                    "embedding": embedding
                })

        # -------------------------------------------------
        # Save document metadata
        # -------------------------------------------------

        pdf_documents[document_id] = {
            "document_id": document_id,
            "filename": file.filename,
            "pages": len(reader.pages),
            "text_length": sum(
                len(item["text"])
                for item in page_texts
            ),
            "chunk_count": len(new_chunks),
            "uploaded_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        # -------------------------------------------------
        # Add new document without deleting old documents
        # -------------------------------------------------

        pdf_chunks.extend(
            new_chunks
        )

        # -------------------------------------------------
        # Persist everything to disk
        # -------------------------------------------------

        save_document_store()

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return {
            "success": True,
            "duplicate": False,
            "document_id": document_id,
            "filename": file.filename,
            "pages": len(reader.pages),
            "text_length": sum(
                len(item["text"])
                for item in page_texts
            ),
            "chunk_count": len(new_chunks),
            "total_documents": len(pdf_documents),
            "total_chunks": len(pdf_chunks),
            "processing_seconds": round(
                time.time() - upload_started_at,
                2
            ),
            "message": (
                "PDF uploaded, chunked, embedded "
                "and permanently indexed successfully."
            )
        }

    except Exception as e:

        print(
            "========== PDF ERROR =========="
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "==============================="
        )

        return {
            "success": False,
            "message": f"PDF Error: {str(e)}"
        }


# =========================================================
# List Uploaded Documents
# =========================================================

@app.get("/documents")
def list_documents():

    return {
        "success": True,
        "documents": list(
            pdf_documents.values()
        ),
        "total_documents": len(
            pdf_documents
        ),
        "total_chunks": len(
            pdf_chunks
        )
    }


# =========================================================
# Delete One Uploaded Document
# =========================================================

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str
):

    global pdf_chunks

    if document_id not in pdf_documents:
        return {
            "success": False,
            "message": "Document not found."
        }

    filename = pdf_documents[
        document_id
    ]["filename"]

    pdf_chunks = [
        chunk
        for chunk in pdf_chunks
        if chunk["document_id"] != document_id
    ]

    del pdf_documents[
        document_id
    ]

    save_document_store()

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "total_documents": len(
            pdf_documents
        ),
        "total_chunks": len(
            pdf_chunks
        ),
        "message": "Document deleted successfully."
    }



# =========================================================
# Ask Question From PDF
# =========================================================

@app.post("/ask-pdf")
def ask_pdf(
    request: PDFQuestionRequest
):

    try:

        # -------------------------------------------------
        # Check PDF knowledge
        # -------------------------------------------------

        if not pdf_chunks:
            return {
                "success": False,
                "answer": "Please upload a PDF first."
            }

        # -------------------------------------------------
        # Limit top_k
        # -------------------------------------------------

        top_k = max(
            1,
            min(
                request.top_k,
                len(pdf_chunks)
            )
        )

        # -------------------------------------------------
        # Create question embedding
        # -------------------------------------------------

        question_embedding = create_embedding(
            request.question
        )

        # -------------------------------------------------
        # Calculate similarities across ALL documents
        # -------------------------------------------------

        results = []

        for chunk in pdf_chunks:

            score = cosine_similarity(
                question_embedding,
                chunk["embedding"]
            )

            results.append({
                "score": score,
                "text": chunk["text"],
                "filename": chunk["filename"],
                "page": chunk.get("page"),
                "document_id": chunk["document_id"]
            })

        # -------------------------------------------------
        # Sort by relevance
        # -------------------------------------------------

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # -------------------------------------------------
        # Select top results
        # -------------------------------------------------

        top_results = results[:top_k]

        # -------------------------------------------------
        # Build context with source information
        # -------------------------------------------------

        context_parts = []

        for index, result in enumerate(
            top_results,
            start=1
        ):

            page_info = ""

            if result.get("page") is not None:
                page_info = (
                    f", Page {result['page']}"
                )

            context_parts.append(
                f"""
SOURCE {index}:
File: {result["filename"]}{page_info}
Content:
{result["text"]}
"""
            )

        context = "\n\n".join(
            context_parts
        )

        # -------------------------------------------------
        # Better Multi-Document RAG Prompt
        # -------------------------------------------------

        prompt = f"""

You are Akhil AI's document question-answering assistant.

You have access to relevant sections retrieved from
one or more uploaded PDF documents.

Answer the user's question using ONLY the provided
document context.

Rules:

1. Use the retrieved document context as the source
   of truth.

2. Do not invent information that is not supported
   by the provided context.

3. If the answer cannot be found in the provided
   context, say clearly:

   "I couldn't find that information in the uploaded documents."

4. If multiple documents contain relevant information,
   combine the information carefully.

5. Do not assume that information from one document
   applies to another document.

6. When useful, mention the relevant document filename
   and page number naturally in the answer.

7. Give a clear, concise and natural answer.

RETRIEVED DOCUMENT CONTEXT:
================================

{context}

================================

USER QUESTION:

{request.question}

"""

        # -------------------------------------------------
        # Gemini With Retry
        # -------------------------------------------------

        response = generate_with_retry(
            prompt
        )

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return {
            "success": True,
            "answer": response.text,
            "sources": [
                {
                    "document_id": item["document_id"],
                    "filename": item["filename"],
                    "page": item.get("page"),
                    "score": round(
                        item["score"],
                        4
                    )
                }
                for item in top_results
            ]
        }

    except Exception as e:

        print(
            "========== PDF QUESTION ERROR =========="
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "========================================"
        )

        return {
            "success": False,
            "answer": f"PDF Question Error: {str(e)}"
        }



# =========================================================
# Ask About Akhil
# =========================================================

@app.post("/ask-akhil")
def ask_akhil(
    request: AkhilQuestionRequest
):

    try:

        # -------------------------------------------------
        # Check Knowledge Base
        # -------------------------------------------------

        if not AKHIL_KNOWLEDGE.strip():

            return {

                "success": False,

                "answer":
                    "Akhil knowledge base is empty."

            }


        # -------------------------------------------------
        # Akhil Knowledge Prompt
        # -------------------------------------------------

        prompt = f"""

You are Akhil AI, a personal AI assistant
that knows about Akhil Pidathala.

Answer the user's question using ONLY
the provided Akhil knowledge.

Rules:

1. Use only information present
   in the knowledge.

2. Do not invent personal information.

3. If the information is not available,
   say exactly:

"I couldn't find that information
in Akhil's knowledge base."

4. Give a clear, natural and
   concise answer.

5. Do not mention the internal
   knowledge files.

6. If the user asks about Akhil,
   answer in third person.

AKHIL KNOWLEDGE:
================================

{AKHIL_KNOWLEDGE}

================================

USER QUESTION:

{request.question}

"""


        # -------------------------------------------------
        # Gemini With Retry
        # -------------------------------------------------

        response = generate_with_retry(
            prompt
        )


        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return {

            "success": True,

            "answer":
                response.text

        }


    except Exception as e:

        print(
            "========== AKHIL KNOWLEDGE ERROR =========="
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "==========================================="
        )


        return {

            "success": False,

            "answer":
                f"Akhil Knowledge Error: {str(e)}"

        }
# =========================================================
# Automatic Intent Router
# =========================================================

class RouterRequest(BaseModel):

    message: str

    history: list = []


def detect_intent(message):

    text = message.lower().strip()


    # -----------------------------------------------------
    # Akhil Knowledge Keywords
    # -----------------------------------------------------

    akhil_keywords = [

        "who is akhil",
        "who's akhil",
        "about akhil",
        "akhil's skills",
        "akhil skills",
        "akhil's projects",
        "akhil projects",
        "akhil's education",
        "akhil education",
        "akhil's internship",
        "akhil internship",
        "akhil's achievements",
        "akhil achievements",
        "what did akhil",
        "tell me about akhil"

    ]


    for keyword in akhil_keywords:

        if keyword in text:

            return "akhil"


    # -----------------------------------------------------
    # PDF Keywords
    # -----------------------------------------------------

    pdf_keywords = [

        "according to the pdf",
        "from the pdf",
        "in the pdf",
        "from this pdf",
        "this pdf",
        "uploaded pdf",
        "document",
        "uploaded document"

    ]


    for keyword in pdf_keywords:

        if keyword in text:

            return "pdf"


    # -----------------------------------------------------
    # Default
    # -----------------------------------------------------

    return "normal"
# =========================================================
# Automatic Chat Router
# =========================================================

@app.post("/route-chat")
def route_chat(request: RouterRequest):

    try:

        intent = detect_intent(
            request.message
        )


        # -------------------------------------------------
        # AKHIL KNOWLEDGE
        # -------------------------------------------------

        if intent == "akhil":

            response = ask_akhil(
                AkhilQuestionRequest(
                    question=request.message
                )
            )

            return {

                "success": response.get(
                    "success",
                    False
                ),

                "intent": "akhil",

                "answer": response.get(
                    "answer",
                    ""
                )

            }


        # -------------------------------------------------
        # PDF
        # -------------------------------------------------

        elif intent == "pdf":

            response = ask_pdf(
                PDFQuestionRequest(
                    question=request.message
                )
            )

            return {

                "success": response.get(
                    "success",
                    False
                ),

                "intent": "pdf",

                "answer": response.get(
                    "answer",
                    ""
                ),

                "sources": response.get(
                    "sources",
                    []
                )

            }


        # -------------------------------------------------
        # NORMAL CHAT
        # -------------------------------------------------

        else:

            response = chat(
                ChatRequest(
                    message=request.message,
                    history=request.history
                )
            )

            return {

                "success": response.get(
                    "success",
                    False
                ),

                "intent": "normal",

                "answer": response.get(
                    "answer",
                    ""
                )

            }


    except Exception as e:

        print(
            "========== ROUTER ERROR =========="
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "=================================="
        )


        return {

            "success": False,

            "intent": "error",

            "answer":
                f"Router Error: {str(e)}"

        }