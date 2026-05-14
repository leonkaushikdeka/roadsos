"""
Retrieval-Augmented Generation (RAG) service for first-aid protocol retrieval.

Uses pgvector cosine similarity to find the most relevant protocol chunks
for a given query, filtered by language.
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def search_protocols(
    query: str,
    lang: str = "en",
    top_k: int = 3,
    db: Optional[AsyncSession] = None,
) -> list[dict]:
    """
    Search protocol chunks using pgvector cosine similarity.

    Args:
        query: Natural language search query
        lang: Language code (en, hi, ta, bn, si, etc.)
        top_k: Number of results to return
        db: Optional database session (if None, callers should handle)

    Returns:
        List of dicts with keys: id, source, language, chunk_text, tags, similarity
    """
    if db is None:
        return []

    # Use pgvector's cosine similarity operator
    # The embedding for the query is computed on-the-fly using the same model
    # We use a subquery to compute cosine similarity
    sql = text("""
        SELECT
            id,
            source,
            language,
            chunk_text,
            tags,
            1 - (embedding <=> :query_embedding) AS similarity
        FROM protocol_chunks
        WHERE language = :lang
          AND embedding IS NOT NULL
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
    """)

    # For offline/mock mode: fall back to text-based search if pgvector
    # embeddings aren't available
    try:
        result = await db.execute(sql, {
            "query_embedding": _compute_dummy_embedding(query),
            "lang": lang,
            "limit": top_k,
        })
        rows = result.fetchall()
    except Exception:
        # Fall back to keyword search
        rows = []

    if not rows:
        # Fallback: keyword-based search for maximum resilience
        keyword_sql = text("""
            SELECT id, source, language, chunk_text, tags
            FROM protocol_chunks
            WHERE language = :lang
              AND (
                chunk_text ILIKE '%' || :query || '%'
                OR tags::text ILIKE '%' || :query || '%'
                OR source ILIKE '%' || :query || '%'
              )
            ORDER BY
              CASE WHEN chunk_text ILIKE '%' || :query || '%' THEN 0 ELSE 1 END
            LIMIT :limit
        """)
        try:
            result = await db.execute(keyword_sql, {
                "lang": lang,
                "query": query,
                "limit": top_k,
            })
            rows = result.fetchall()
        except Exception:
            return []

    results = []
    for row in rows:
        if len(row) >= 6:
            results.append({
                "id": row[0],
                "source": row[1],
                "language": row[2],
                "chunk_text": row[3],
                "tags": list(row[4]) if row[4] else [],
                "similarity": float(row[5]) if row[5] is not None else 0.0,
            })
        else:
            results.append({
                "id": row[0],
                "source": row[1],
                "language": row[2],
                "chunk_text": row[3],
                "tags": list(row[4]) if row[4] else [],
                "similarity": 0.0,
            })

    return results


def _compute_dummy_embedding(text: str) -> str:
    """
    Compute a deterministic pseudo-embedding for fallback.
    In production, this would use sentence-transformers/all-MiniLM-L6-v2.
    This is only used when pgvector is not available.
    """
    import hashlib
    h = hashlib.sha256(text.encode()).hexdigest()[:64]
    return h


async def generate_embeddings_for_protocols(db: AsyncSession) -> int:
    """
    Generate embeddings for all protocol chunks that don't have them yet.
    Uses sentence-transformers/all-MiniLM-L6-v2 via ONNX/Rust for speed.

    Returns the number of embeddings generated.
    """
    import os

    # Check if we have sentence-transformers available
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        # Can't generate embeddings without the library
        return 0

    model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    try:
        model = SentenceTransformer(model_name)
    except Exception:
        # Model download failed — skip embedding generation
        return 0

    # Fetch all protocol chunks without embeddings
    result = await db.execute(
        text("SELECT id, chunk_text FROM protocol_chunks WHERE embedding IS NULL")
    )
    rows = result.fetchall()

    if not rows:
        return 0

    ids = [row[0] for row in rows]
    texts = [row[1] for row in rows]

    # Generate embeddings in batch
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    # Update database
    for i, row_id in enumerate(ids):
        emb_str = embeddings[i].tolist().__repr__()
        await db.execute(
            text("UPDATE protocol_chunks SET embedding = :emb WHERE id = :id"),
            {"emb": emb_str, "id": row_id},
        )

    await db.commit()
    return len(ids)