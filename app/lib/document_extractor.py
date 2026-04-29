import re
import asyncio
from io import BytesIO
from base64 import b64decode
from typing import Literal, TypedDict, NotRequired

from pypdf import PdfReader

SupportedFormat = Literal["text", "pdf", "markdown"]


def detect_format(filename: str) -> SupportedFormat:
    """Detect the format of a document based on its file extension."""
    ext = filename.split(".")[-1].lower()

    match ext:
        case "txt":
            return "text"
        case "pdf":
            return "pdf"
        case "md":
            return "markdown"
        case _:
            raise ValueError(f"Unsupported file format: .{ext}")


class _ExtractedText(TypedDict):
    text: str
    page_count: NotRequired[int]


async def extract_text(
    content: BytesIO | str, format: SupportedFormat
) -> _ExtractedText:
    """Extract text from a document based on its format."""
    match format:
        case "text":
            text = (
                content if isinstance(content, str) else content.read().decode("utf-8")
            )
            return {"text": text}
        case "markdown":
            text = (
                content if isinstance(content, str) else content.read().decode("utf-8")
            )
            return {"text": strip_markdown(text)}
        case "pdf":
            if isinstance(content, str):
                content = BytesIO(b64decode(content))

            reader = await asyncio.to_thread(PdfReader, content)
            text = "\n".join(page.extract_text() for page in reader.pages)

            return {"text": clean_extracted_text(text), "page_count": len(reader.pages)}

        case _:
            raise ValueError(f"Unsupported format: {format}")


def strip_markdown(text: str) -> str:
    """Strip markdown formatting from text."""
    text = re.sub(r"#{1,6}\s+", "", text)  # Headers
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)  # Bold/italic
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # Code blocks
    text = re.sub(r"^[\-*+]\s+", "", text, flags=re.MULTILINE)  # List markers
    return text.strip()


def clean_extracted_text(text: str) -> str:
    """Clean extracted text."""
    text = re.sub(r"\r\n", "\n", text)  # Normalize line endings
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse excessive newlines
    text = re.sub(r"\s{3,}", " ", text)  # Collapse excessive spaces
    return text.strip()
