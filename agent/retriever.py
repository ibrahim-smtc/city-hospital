"""
RAG Retriever for City Hospital Knowledge Base.

Loads all markdown files from the `kb/` directory, chunks them,
embeds them locally using sentence-transformers (no internet needed after first download),
stores them in a local FAISS vector index, and exposes a `retriever`
object for use in the LangGraph agent tools.

Embedding Model: sentence-transformers/all-MiniLM-L6-v2
  - ~90MB download (happens once, then cached locally)
  - Runs 100% offline after first download
  - Fast and efficient for semantic search
"""

import os
import glob
import warnings

# Suppress deprecation warnings from langchain-community (harmless, library sunset notice)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load .env FIRST — before any HuggingFace imports, because HF Hub
# checks for HF_TOKEN at import time, not at call time.
from dotenv import load_dotenv
load_dotenv()

# Set HF_TOKEN explicitly so HuggingFace Hub sees it before initializing
_hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINFACE_API_TOKEN")
if _hf_token:
    os.environ["HF_TOKEN"] = _hf_token

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# ─── Load environment variables (.env) ─────────────────────────────────────────
load_dotenv()

# ─── Constants ──────────────────────────────────────────────────────────────────
# Compute the project ROOT directory regardless of where you run the script from.
# __file__ = .../demo_api_workspace/agent/retriever.py
# ROOT     = .../demo_api_workspace/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Root directory containing all the scraped markdown files
KB_DIR = os.path.join(ROOT_DIR, "kb")

# Where the FAISS index will be saved and loaded from on disk
VECTORSTORE_PATH = os.path.join(ROOT_DIR, "agent", "vectorstore")

# Lightweight local embedding model — only ~90MB, fast, runs 100% offline
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ─── Initialize the embedding model (local, no API key needed) ───────────────
def get_embeddings():
    """
    Returns a local HuggingFaceEmbeddings instance.
    Downloads the model once on first run (~90MB), then runs fully offline.
    No API key or internet connection needed after the first download.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ─── Step 1: Load all .md documents from the kb/ folder ────────────────────────
def load_all_documents():
    """
    Recursively finds every .md file inside the `kb/` directory and
    loads them as LangChain Document objects.

    Returns:
        list[Document]: A flat list of all loaded documents.
    """
    md_files = glob.glob(os.path.join(KB_DIR, "**", "*.md"), recursive=True)

    # Exclude meta/index files — they are high-level summaries that mention
    # everything and create noise, causing the retriever to prefer them over
    # the actual specific content files.
    EXCLUDE_FILES = {"INDEX.md", "SCRAPE_NOTES.md", "_manifest.json"}
    md_files = [
        f for f in md_files
        if os.path.basename(f) not in EXCLUDE_FILES
    ]

    if not md_files:
        raise FileNotFoundError(
            f"No markdown files found in '{KB_DIR}/'. "
            "Make sure the kb/ directory exists and contains .md files."
        )

    all_docs = []
    for filepath in md_files:
        try:
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()
            all_docs.extend(docs)
        except Exception as e:
            print(f"  [WARN] Could not load {filepath}: {e}")

    print(f"[Retriever] Loaded {len(all_docs)} documents from {len(md_files)} markdown files.")
    return all_docs


# ─── Step 2: Chunk, embed, and build the FAISS index ───────────────────────────
def build_vectorstore():
    """
    Loads all documents, splits them into chunks, generates BGE embeddings,
    builds a FAISS vector store, and saves it to disk.

    Returns:
        FAISS: The built and saved vector store object.
    """
    print("[Retriever] Building FAISS vector store from scratch...")
    print(f"[Retriever] Using embedding model: {EMBEDDING_MODEL}")

    # Load all raw markdown documents
    documents = load_all_documents()

    # Split into smaller chunks for better retrieval accuracy
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"[Retriever] Split into {len(chunks)} chunks.")

    print(f"[Retriever] Using local embedding model: {EMBEDDING_MODEL}")
    print("[Retriever] Downloading model on first run (~90MB), then cached locally...")
    embeddings = get_embeddings()

    # Build the FAISS index from the document chunks
    print("[Retriever] Generating embeddings and building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Persist the index to disk so we don't rebuild it every server restart
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    vectorstore.save_local(VECTORSTORE_PATH)
    print(f"[Retriever] FAISS index saved to '{VECTORSTORE_PATH}'.")

    return vectorstore


# ─── Step 3: Load from disk (or build if not found) ────────────────────────────
def load_vectorstore():
    """
    Loads the FAISS vector store from disk if it exists.
    If not, builds it from the kb/ markdown files and saves it.

    Returns:
        FAISS: The loaded (or newly built) vector store object.
    """
    embeddings = get_embeddings()

    # Check if the saved index already exists on disk
    index_file = os.path.join(VECTORSTORE_PATH, "index.faiss")
    if os.path.exists(index_file):
        print(f"[Retriever] Loading existing FAISS index from '{VECTORSTORE_PATH}'...")
        vectorstore = FAISS.load_local(
            VECTORSTORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True,  # required by LangChain for local files
        )
        print("[Retriever] FAISS index loaded successfully.")
        return vectorstore

    # Index not found — build from scratch
    return build_vectorstore()


# ─── Module-level initialization ───────────────────────────────────────────────
# This runs once when `retriever.py` is first imported.
# The `retriever` object is what agent/tools.py will import and use.
vectorstore = load_vectorstore()
# similarity_score_threshold: for sentence-transformers embeddings,
# cosine similarity scores typically fall between 0.2 and 0.6.
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.25, "k": 5},
)


# ─── Utility: Rebuild the index (call manually if kb/ files change) ─────────────
def rebuild_index():
    """
    Forces a full rebuild of the FAISS index from the kb/ markdown files.
    Call this if you add or update files in the kb/ directory.
    """
    import shutil
    if os.path.exists(VECTORSTORE_PATH):
        shutil.rmtree(VECTORSTORE_PATH)
        print(f"[Retriever] Deleted old index at '{VECTORSTORE_PATH}'.")
    return build_vectorstore()


# ─── Interactive Test Section ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  CITY HOSPITAL RAG RETRIEVER - INTERACTIVE MODE")
    print("  Type your question below (or type 'exit' / 'q' to quit)")
    print("="*60 + "\n")

    while True:
        try:
            query = input("\n🔍 Enter question: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting interactive test. Goodbye!")
                break

            print("-" * 50)
            results = retriever.invoke(query)

            if not results:
                print("  ❌ No relevant documents found above the threshold.")
            else:
                for i, doc in enumerate(results, 1):
                    source = doc.metadata.get("source", "Unknown source")
                    source_name = os.path.basename(source)
                    content_preview = doc.page_content[:250].replace("\n", " ").strip()
                    print(f"  [{i}] Source: {source_name}")
                    print(f"      Preview: {content_preview}...")
                    print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive test. Goodbye!")
            break


