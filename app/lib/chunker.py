import math
from typing import TypedDict


def old_split_into_chunks(text: str, max_words_per_chunk: int) -> list[str]:
    """Split text into chunks based on word count."""
    words = text.split(" ")
    chunks: list[str] = []

    for i in range(0, len(words), max_words_per_chunk):
        chunk = " ".join(words[i : i + max_words_per_chunk])
        if chunk := chunk.strip():
            chunks.append(chunk)

    return chunks if len(chunks) > 0 else [text.strip()]


def old_estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text."""
    return math.ceil(len(text.split()) * 1.33)


class _ChunkMetadata(TypedDict):
    start_char: int
    # Was not used anywhere but was in the interface -> end_char: int


class _Chunk(TypedDict):
    text: str
    index: int
    token_estimate: int
    metadata: _ChunkMetadata


SEPARATORS = [
    "\n\n",  # Paragraphs
    "\n",  # Lines
    ". ",  # Sentences
    "? ",  # Questions
    "! ",  # Exclamations
    " ",  # Words (last resort)
]


def chunk_document(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    min_chunk_tokens: int = 50,
) -> list[_Chunk]:
    """Chunk a document into smaller pieces based on token count."""
    raw_chunks = recursive_split(text, SEPARATORS, max_tokens)
    with_overlap = add_overlap(raw_chunks, overlap_tokens)

    # Filter out chunks that are too small
    with_overlap = [
        chunk
        for chunk in with_overlap
        if estimate_tokens(chunk["text"]) >= min_chunk_tokens
    ]

    return [
        {
            "text": chunk["text"],
            "index": index,
            "token_estimate": estimate_tokens(chunk["text"]),
            "metadata": {"start_char": chunk["start_char"]},
        }
        for index, chunk in enumerate(with_overlap)
    ]


class _SplitChunk(TypedDict):
    text: str
    start_char: int


def recursive_split(
    text: str, separators: list[str], max_tokens: int
) -> list[_SplitChunk]:
    """Recursively split text using a list of separators."""
    if estimate_tokens(text) <= max_tokens:
        return [{"text": text, "start_char": 0}]

    # Find the first separator that actually splits the text
    for sep in separators:
        parts = [p.strip() for p in text.split(sep)]
        if len(parts) <= 1:
            continue

        # Try to combine adjacent parts into chunks under the limit
        chunks: list[_SplitChunk] = []
        current = ""
        char_offset = 0
        chunk_start = 0

        for part in parts:
            combined = current + sep + part if current else part

            if estimate_tokens(combined) > max_tokens and current:
                chunks.append({"text": current, "start_char": chunk_start})
                current = part
                chunk_start = char_offset
            else:
                if not current:
                    chunk_start = char_offset
                current = combined

            char_offset += len(part) + len(sep)

        if current:
            chunks.append({"text": current, "start_char": chunk_start})

        result_chunks: list[_SplitChunk] = []
        # Recursively split any chunks that are still too big
        for chunk in chunks:
            if estimate_tokens(chunk["text"]) > max_tokens:
                result_chunks.extend(
                    recursive_split(
                        chunk["text"],
                        separators[separators.index(sep) + 1 :],
                        max_tokens,
                    )
                )
            else:
                result_chunks.append(chunk)
        return result_chunks

    # No separator worked. Return the text as-is.
    return [{"text": text, "start_char": 0}]


def add_overlap(chunks: list[_SplitChunk], overlap_tokens: int) -> list[_SplitChunk]:
    """Add overlap to chunks."""
    if overlap_tokens == 0 or len(chunks) <= 1:
        return chunks

    for i, chunk in enumerate(chunks):
        if i == 0:
            continue

        prev_text = chunks[i - 1]["text"]
        overlap_text = get_last_n_tokens(prev_text, overlap_tokens)

        chunk["text"] = overlap_text + "\n" + chunk["text"]

    return chunks


def get_last_n_tokens(text: str, n: int) -> str:
    """Get the last n tokens from a text."""
    words = text.split(" ")
    words_needed = math.ceil(n / 1.3)  # Estimate words needed for n tokens
    return " ".join(words[-words_needed:]) if len(words) >= words_needed else text


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text."""
    return math.ceil(len(text) * 4)
