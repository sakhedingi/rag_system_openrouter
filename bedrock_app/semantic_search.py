import os
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from .embedding import embed_with_openrouter, cosine_similarity

def load_documents_from_folder(folder_path):
    documents = []
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)

        if filename.endswith(".txt"):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"[ERROR] Failed to read TXT: {filename}  {e}")
                continue
        elif filename.endswith(".pdf"):
            try:
                content = extract_pdf_text(full_path)
            except Exception as e:
                print(f"[ERROR] Failed to read PDF: {filename}  {e}")
                continue
        elif filename.endswith(".docx"):
            try:
                doc = Document(full_path)
                content = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                print(f"[ERROR] Failed to read DOCX: {filename}  {e}")
                continue
        else:
            continue

        documents.append({
            "filename": filename,
            "content": content
        })

    return documents

def build_vector_store_from_folder(folder_path, embed_model_id):
    docs = load_documents_from_folder(folder_path)
    store = []
    for doc in docs:
        embedding = embed_with_openrouter(embed_model_id, doc["content"])
        if embedding:
            store.append({
                "filename": doc["filename"],
                "content": doc["content"],
                "embedding": embedding
            })
            print(f"[OK] Embedded: {doc['filename']}")
        else:
            print(f"[ERROR] Failed to embed: {doc['filename']}")
    return store

def semantic_search_local(query_text, embed_model_id, store, top_k=3):
    query_embedding = embed_with_openrouter(embed_model_id, query_text)
    if not query_embedding:
        print("Failed to generate embedding for query.")
        return []
    scored = []
    for entry in store:
        score = cosine_similarity(query_embedding, entry["embedding"])
        scored.append((entry["filename"], score, entry["content"]))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
