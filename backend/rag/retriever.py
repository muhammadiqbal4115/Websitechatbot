from rag.ingest import get_chroma_collection


def retrieve_context(query: str, n_results: int = 4) -> list[dict]:
    """
    Query ChromaDB for the most relevant FAQ entries.
    Returns a list of {document, question, category, distance} dicts.
    """
    collection = get_chroma_collection()

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        print(f"[Retriever] ChromaDB query failed: {e}")
        return []

    hits = []
    if results and results.get("documents"):
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "document": doc,
                    "question": meta.get("question", ""),
                    "category": meta.get("category", ""),
                    "distance": dist,
                }
            )

    # Filter out low-relevance hits (cosine distance > 0.6 means not very similar)
    hits = [h for h in hits if h["distance"] < 0.6]
    return hits
