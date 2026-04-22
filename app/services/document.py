import asyncio
from uuid import UUID
from typing import Any
from datetime import UTC, datetime

from tortoise.expressions import Q

from app.lib.cache import CACHE_TTL, cache_get_or_set
from app.lib.events import APP_EVENTS
from app.orm.models import Document
from app.queues.jobs import document_queue, queue_document_for_processing
from app.validators.document import ListDocumentsSchema
from app.lib.response_formatter import (
    error_response,
    success_response,
    paginated_success_response,
)


async def list_documents(user_id: UUID, options: ListDocumentsSchema) -> dict[str, Any]:
    """List documents for a user."""
    query = Document.filter(user_id=user_id, deleted_at=None)

    if options.status:
        query = query.filter(status=options.status)

    if options.search:
        query = query.filter(
            Q(title__icontains=options.search) | Q(content__icontains=options.search)
        )

    if options.sort_by:
        obj_query = query.order_by(
            f"{'-' if options.sort_order == 'desc' else ''}{options.sort_by}"
        )
    else:
        obj_query = query.order_by("-created_at")

    documents, total = await asyncio.gather(
        obj_query.offset((options.page - 1) * options.limit)
        .limit(options.limit)
        .only(
            "id",
            "title",
            "filename",
            "status",
            "chunk_count",
            "created_at",
            "updated_at",
        ),
        query.count(),
    )

    return paginated_success_response(
        message="Documents retrieved successfully",
        metadata={
            "page": options.page,
            "limit": options.limit,
            "total": total,
        },
        data=[
            {
                "id": doc.id,
                "title": doc.title,
                "status": doc.status,
                "filename": doc.filename,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
            }
            for doc in documents
        ],
    )


async def get_document(document_id: UUID, user_id: UUID) -> dict[str, Any]:
    """Get document details."""

    async def _fetch_document() -> dict[str, Any] | None:
        doc = await Document.get_or_none(
            id=document_id, user_id=user_id, deleted_at=None
        ).only(
            "id",
            "title",
            "filename",
            "status",
            "chunk_count",
            "created_at",
            "updated_at",
        )
        return (
            {
                "id": str(doc.id),
                "title": doc.title,
                "status": doc.status,
                "filename": doc.filename,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            }
            if doc
            else None
        )

    document = await cache_get_or_set(
        key=f"doc:{document_id}",
        type=dict[str, Any],
        ttl_seconds=CACHE_TTL.DOCUMENT.value,
        fetch_func=_fetch_document,
    )

    if not document:
        return error_response(404, "Document not found")

    return success_response(message="Document retrieved successfully", data=document)


async def create_document(title: str, content: str, user_id: UUID) -> dict[str, Any]:
    """Create a new document."""
    document = await Document.create(
        title=title,
        content=content,
        filename="-".join(title.lower().split()),
        user_id=user_id,
        status="pending",
    )

    job_id = await queue_document_for_processing(
        document_id=document.id.hex, user_id=user_id.hex
    )

    APP_EVENTS.emit(
        "doc:created",
        {
            "document_id": document.id.hex,
            "user_id": user_id.hex,
            "title": document.title,
        },
    )

    return success_response(
        message="Document created successfully",
        data={
            "document": {
                "id": document.id,
                "title": document.title,
                "status": document.status,
                "filename": document.filename,
                "chunk_count": document.chunk_count,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            },
            "job_id": job_id,
        },
    )


async def delete_document(document_id: UUID, user_id: UUID) -> dict[str, Any]:
    """Soft delete a document."""
    document = await Document.get_or_none(id=document_id, user_id=user_id)

    if not document or document.deleted_at is not None:
        return error_response(404, "Document not found")

    document.deleted_at = datetime.now(UTC)
    document.deleted_by = user_id
    await document.save()

    return success_response(message="Document deleted successfully")


async def get_processing_status(document_id: UUID, user_id: UUID) -> dict[str, Any]:
    """Get the processing status of a document."""
    document = await Document.get_or_none(id=document_id, user_id=user_id).only(
        "id", "user_id", "status", "error"
    )

    if not document:
        return error_response(404, "Document not found")

    jobs = await document_queue.getJobs(["active", "waiting"])  # pyright: ignore[reportUnknownMemberType]
    active_job = None

    for job in jobs:
        if job and job.data.get("document_id") == document_id.hex:  # type: ignore
            active_job = job
            break

    return success_response(
        message="Document processing status retrieved successfully",
        data={
            "status": document.status,
            "error": document.error,
            "progress": active_job.progress if active_job else None,  # type: ignore
        },
    )
