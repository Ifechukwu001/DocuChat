from uuid import UUID
from typing import Annotated

from fastapi import Query, Depends, Request, APIRouter, status

from app.services import document as document_service
from app.middleware.auth import UserInfo, authenticate
from app.validators.document import ListDocumentsSchema, CreateDocumentSchema
from app.middleware.authorize import require_permission
from app.middleware.ratelimiter import api_limiter, upload_limiter

router = APIRouter(dependencies=[Depends(authenticate), Depends(api_limiter)])


@router.get("", dependencies=[Depends(require_permission("documents:read"))])
async def list_documents(
    user: Annotated[UserInfo, Depends(authenticate)],
    filter: Annotated[ListDocumentsSchema, Query()],
) -> dict[str, object]:
    """List documents."""
    return await document_service.list_documents(user["id"], filter)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_permission("documents:create")),
        Depends(upload_limiter),
    ],
)
async def create_document(
    user: Annotated[UserInfo, Depends(authenticate)],
    details: CreateDocumentSchema,
    request: Request,
) -> dict[str, object]:
    """Create a new document."""
    return await document_service.create_document(
        details.title,
        details.content,
        user["id"],
        correlation_id=UUID(request.state.correlation_id),
    )


@router.get("/{id}", dependencies=[Depends(require_permission("documents:read"))])
async def get_document(
    id: UUID, user: Annotated[UserInfo, Depends(authenticate)]
) -> dict[str, object]:
    """Get document details."""
    return await document_service.get_document(id, user["id"])


@router.delete(
    "/{id}",
    dependencies=[Depends(require_permission("documents:delete"))],
)
async def delete_document(
    id: UUID, user: Annotated[UserInfo, Depends(authenticate)]
) -> dict[str, object]:
    """Delete a document."""
    return await document_service.delete_document(id, user["id"])


@router.get(
    "/{id}/processing-status",
    dependencies=[Depends(require_permission("documents:read"))],
)
async def get_processing_status(
    id: UUID, user: Annotated[UserInfo, Depends(authenticate)]
) -> dict[str, object]:
    """Get the processing status of a document."""
    return await document_service.get_processing_status(id, user["id"])
