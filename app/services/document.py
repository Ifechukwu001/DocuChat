import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from tortoise.expressions import Q

from app.lib.response_formatter import error_response, paginated_success_response
from app.orm.models import Document
from app.validators.document import ListDocumentsSchema


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
                "id": doc.id.hex,
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


async def delete_document(document_id: UUID, user_id: UUID) -> dict[str, Any]:
    """Soft delete a document."""
    document = await Document.get_or_none(id=document_id, user_id=user_id)

    if not document or document.deleted_at is not None:
        return error_response(404, "Document not found")

    document.deleted_at = datetime.now(UTC)
    document.deleted_by = user_id
    await document.save()

    return paginated_success_response(
        message="Document deleted successfully",
        metadata={
            "page": 1,
            "limit": 1,
            "total": 1,
        },
        data=[
            {
                "id": document.id.hex,
                "title": document.title,
                "status": document.status,
                "filename": document.filename,
                "chunk_count": document.chunk_count,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
        ],
    )


"""
// In document.service.ts createDocument:
appEvents.emit(DOC_EVENTS.CREATED, {
  userId: user.id,
  documentId: doc.id,
  title: doc.title,
  fileSizeBytes: doc.fileSizeBytes,
});

// In document.service.ts deleteDocument:
appEvents.emit(DOC_EVENTS.DELETED, {
  deletedBy: userId,
  documentId: doc.id,
  title: doc.title,
});

"""
