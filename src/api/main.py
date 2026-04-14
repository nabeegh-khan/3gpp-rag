import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# paths
CHROMA_PATH = r"C:\Projects\3gpp-rag\chroma_db"

# global chain variable - gets initialized on startup
rag_chain = None


def format_docs(docs):
    # attach source metadata to each chunk so the LLM can cite it
    formatted = []
    for doc in docs:
        source = doc.metadata.get("title", "Unknown")
        page = doc.metadata.get("page", "Unknown")
        formatted.append(f"[{source}, Page {page}]\n{doc.page_content}")
    return "\n\n".join(formatted)


def build_chain():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
You are a technical assistant specializing in 3GPP wireless standards.
Answer the question using ONLY the context provided below.
For every piece of information you use, cite the source document and page number.
If the answer is not in the context, say "I don't have enough information in the
loaded specifications to answer this question."

Context:
{context}

Question:
{question}

Answer (with citations):
""")

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


@asynccontextmanager
async def lifespan(app: FastAPI):
    # load the chain once when the server starts
    global rag_chain
    print("Loading RAG chain...")
    rag_chain = build_chain()
    print("RAG chain ready")
    yield
    print("Shutting down")


app = FastAPI(
    title="3GPP RAG API",
    description="Query 3GPP 5G/6G technical specifications using natural language",
    version="1.0.0",
    lifespan=lifespan
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str


@app.get("/health")
def health():
    return {"status": "ok", "chain_loaded": rag_chain is not None}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG chain not loaded")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    answer = rag_chain.invoke(request.question)
    return QueryResponse(question=request.question, answer=answer)