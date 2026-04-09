from uuid import UUID
from typing import Annotated

from fastapi import Query, Depends, APIRouter

from app.middleware.auth import authenticate
from app.validators.document import ListDocumentsSchema, CreateDocumentSchema

router = APIRouter(dependencies=[Depends(authenticate)])


@router.get("")
async def list_documents(
    filter: Annotated[ListDocumentsSchema, Query()],
) -> dict[str, object]:
    """List documents."""
    return {}


@router.post("")
async def create_document(details: CreateDocumentSchema) -> dict[str, object]:
    """Create a new document."""
    return {}


@router.get("/{id}")
async def get_document(id: UUID) -> dict[str, object]:
    """Get document details."""
    return {}


@router.delete("/{id}")
async def delete_document(id: UUID) -> dict[str, object]:
    """Delete a document."""
    return {}
