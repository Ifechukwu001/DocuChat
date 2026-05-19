from .agent import AIAuditLog, ReviewQueue, PromptTemplate
from .users import Role, User, UserRole, Permission, RefreshToken, RolePermission
from .webhook import WebhookEvent
from .documents import Chunk, Document
from .conversations import Message, Conversation
from .observability import AITrace, UsageLog

__models__: list[type] = [
    Role,
    User,
    Chunk,
    AITrace,
    Message,
    Document,
    UsageLog,
    UserRole,
    AIAuditLog,
    Permission,
    ReviewQueue,
    WebhookEvent,
    Conversation,
    RefreshToken,
    PromptTemplate,
    RolePermission,
]
