from uuid import uuid4
from types import SimpleNamespace

import pytest

from app.services import rbac


@pytest.mark.anyio
async def test_get_user_permissions_flattens_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aggregates and deduplicates permission names from a user's roles."""

    class FakeQuery:
        def prefetch_related(self, *_: str) -> FakeQuery:
            return self

        async def all(self) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(
                    role=SimpleNamespace(
                        permissions=[
                            SimpleNamespace(
                                permission=SimpleNamespace(name="docs:read")
                            ),
                            SimpleNamespace(
                                permission=SimpleNamespace(name="docs:write")
                            ),
                        ]
                    )
                ),
                SimpleNamespace(
                    role=SimpleNamespace(
                        permissions=[
                            SimpleNamespace(
                                permission=SimpleNamespace(name="docs:read")
                            ),
                            SimpleNamespace(
                                permission=SimpleNamespace(name="admin:manage")
                            ),
                        ]
                    )
                ),
            ]

    def fake_filter(**_: object) -> FakeQuery:
        return FakeQuery()

    monkeypatch.setattr(rbac.UserRole, "filter", fake_filter)

    permissions = await rbac.get_user_permissions(uuid4())

    assert permissions == {"docs:read", "docs:write", "admin:manage"}
