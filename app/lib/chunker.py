import math


def split_into_chunks(text: str, max_words_per_chunk: int) -> list[str]:
    """Split text into chunks based on word count."""
    words = text.split(" ")
    chunks: list[str] = []

    for i in range(0, len(words), max_words_per_chunk):
        chunk = " ".join(words[i : i + max_words_per_chunk])
        if chunk := chunk.strip():
            chunks.append(chunk)

    return chunks if len(chunks) > 0 else [text.strip()]


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text."""
    return math.ceil(len(text.split()) * 1.33)
