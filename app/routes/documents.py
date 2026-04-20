from uuid import UUID
from typing import Annotated

from fastapi import Query, Depends, APIRouter

from app.services import document as document_service
from app.middleware.auth import authenticate
from app.middleware.authorize import require_permission
from app.validators.document import ListDocumentsSchema, CreateDocumentSchema

router = APIRouter()


@router.get("", dependencies=[Depends(require_permission("documents:read"))])
async def list_documents(
    user_id: Annotated[UUID, Depends(authenticate)],
    filter: Annotated[ListDocumentsSchema, Query()],
) -> dict[str, object]:
    """List documents."""
    return await document_service.list_documents(user_id, filter)


@router.post("", dependencies=[Depends(require_permission("documents:create"))])
async def create_document(details: CreateDocumentSchema) -> dict[str, object]:
    """Create a new document."""
    return {}


@router.get("/{id}", dependencies=[Depends(require_permission("documents:read"))])
async def get_document(id: UUID) -> dict[str, object]:
    """Get document details."""
    return {}


@router.delete(
    "/{id}",
    dependencies=[Depends(require_permission("documents:delete"))],
)
async def delete_document(
    id: UUID, user_id: Annotated[UUID, Depends(authenticate)]
) -> dict[str, object]:
    """Delete a document."""
    return await document_service.delete_document(id, user_id)
