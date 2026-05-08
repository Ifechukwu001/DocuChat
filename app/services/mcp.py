from uuid import UUID
from typing import Any, Literal, TypedDict, NotRequired
from datetime import UTC, datetime

from tortoise.functions import Sum

from app.lib.cache import cache_get, cache_set, cache_expire, cache_incr_float
from app.orm.models import User, UsageLog, AIAuditLog, PromptTemplate
from app.lib.logging import logger
from app.lib.response_formatter import error_response
from app.lib.http.openai_breaker import call_openai

TaskType = Literal["chat", "embedding", "agent", "summary"]


class _Message(TypedDict):
    role: Literal["user", "assistant", "system"] | str
    content: str


class MCPRequest(TypedDict):
    """MCPRequest represents a request to the MCP (Model Control Plane) service."""

    system_prompt: str
    task_type: TaskType
    messages: list[_Message]
    user_id: UUID
    correlation_id: str
    tools: NotRequired[list[Any]]
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]


class _TokensUsed(TypedDict):
    prompt: int
    completion: int


class _TotalTokensUsed(_TokensUsed):
    total: int


class MCPResponse(TypedDict):
    """MCPResponse represents a response from the MCP (Model Control Plane) service."""

    content: str
    tool_calls: NotRequired[list[dict[str, Any]]]
    model: str
    prompt_version: str
    tokens_used: _TotalTokensUsed
    cost_usd: float
    latency_secs: float
    fallback_used: bool


async def mcp_complete(request: MCPRequest) -> MCPResponse:
    """mcp_complete sends a request to the MCP (Model Control Plane) service and returns the response."""
    start_time = datetime.now(UTC)

    # 1. Check budget
    await enforce_budget(request["user_id"])

    # 2. Resolve prompt version
    prompt = await resolve_prompt(request["task_type"])

    # 3. Select model
    model = await route_model(request["task_type"], request["messages"])

    # 4. Call with fallback
    result = await call_with_fallback(
        model, {**request, "system_prompt": prompt["content"]}
    )

    # 5. Track cost
    cost_usd = calculate_cost(result["model"], result["tokens_used"])
    await track_cost(request["user_id"], cost_usd)

    # 6. Audit log
    await audit_log(
        {
            "user_id": request["user_id"],
            "correlation_id": request["correlation_id"],
            "task_type": request["task_type"],
            "model": result["model"],
            "prompt_version": prompt["version"],
            "messages": request["messages"],
            "cost_usd": cost_usd,
            "latency_secs": (datetime.now(UTC) - start_time).total_seconds(),
            "fallback_used": result["fallback_used"],
            "response": result["content"],
        }
    )

    """
    if(request["task_type"] == "chat") {

    // Track Confidence level metric

    }
    """

    return {
        "content": result["content"],
        "tool_calls": result.get("tool_calls", []),
        "model": result["model"],
        "prompt_version": prompt["version"],
        "tokens_used": {
            "prompt": result["tokens_used"]["prompt"],
            "completion": result["tokens_used"]["completion"],
            "total": result["tokens_used"]["total"],
        },
        "cost_usd": cost_usd,
        "latency_secs": (datetime.now(UTC) - start_time).total_seconds(),
        "fallback_used": result["fallback_used"],
    }


class _PromptTemplateDict(TypedDict):
    content: str
    version: str


async def resolve_prompt(task_type: TaskType) -> _PromptTemplateDict:
    """Fetches the active prompt template for the given task type."""
    cache_key = f"prompt:{task_type}:active"
    cached = await cache_get(cache_key, _PromptTemplateDict)
    if cached:
        return cached

    # Load from database
    prompt = (
        await PromptTemplate.filter(task_type=task_type, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if not prompt:
        raise RuntimeError(f"No active prompt for task type: {task_type}")

    result: _PromptTemplateDict = {"content": prompt.content, "version": prompt.version}
    await cache_set(cache_key, result, 300)  # Cache for 5 minutes
    return result


async def resolve_prompt_ab(task_type: TaskType, user_id: UUID) -> _PromptTemplateDict:
    """Fetches the active prompt template for the given task type, with A/B testing."""
    prompts = (
        await PromptTemplate.filter(task_type=task_type, is_active=True)
        .order_by("version")
        .all()
    )

    if len(prompts) <= 1:
        return await resolve_prompt(task_type)  # No A/B test running

    # Deterministic split: hash the user ID to get a consistent bucket
    hash = ord(user_id.hex[0]) + ord(user_id.hex[-1])
    index = hash % len(prompts)

    selected = prompts[index]
    return {"content": selected.content, "version": selected.version}


class ModelConfig(TypedDict):
    """ModelConfig represents the configuration for a model, used for routing decisions."""

    name: str
    cost_per_million_input: float
    cost_per_million_output: float
    max_tokens: int


MODELS: dict[str, ModelConfig] = {
    "gemma2": {
        "name": "gemma2",
        "cost_per_million_input": 2.50,
        "cost_per_million_output": 10.00,
        "max_tokens": 128000,
    },
    "qwen2.5": {
        "name": "qwen2.5",
        "cost_per_million_input": 0.15,
        "cost_per_million_output": 0.60,
        "max_tokens": 128000,
    },
    "qwen2": {
        "name": "qwen2",
        "cost_per_million_input": 0.10,
        "cost_per_million_output": 0.50,
        "max_tokens": 128000,
    },
    "nomic-text-embed": {
        "name": "nomic-text-embed",
        "cost_per_million_input": 0.01,
        "cost_per_million_output": 0.02,
        "max_tokens": 128000,
    },
}

# Task type → default model mapping
MODEL_ROUTING: dict[TaskType, str] = {
    "chat": "gemma2",  # Simple Q&A — cheap model is fine
    "embedding": "nomic-text-embed",  # Embedding model
    "agent": "qwen2",  # Agents need strong reasoning
    "summary": "gemma2",  # Summaries are straightforward
}


async def route_model(task_type: TaskType, messages: list[_Message]) -> ModelConfig:
    """Determines which model to use based on the task type and message content."""
    model_name = MODEL_ROUTING.get(task_type, "")
    return (
        MODELS.get(model_name) or MODELS["qwen2"]  # Default to qwen2 if not found
    )


FALLBACK_CHAINS: dict[str, list[str]] = {
    "gemma2": ["gemma2", "qwen2"],
    "qwen2": ["qwen2", "qwen2.5"],
    "qwen2.5": ["qwen2.5", "gemma2"],
}


async def call_with_fallback(
    primary_model: ModelConfig, request: MCPRequest
) -> MCPResponse:
    """Calls the model with a fallback mechanism in case of failure."""
    chain = FALLBACK_CHAINS.get(primary_model["name"]) or [primary_model["name"]]

    for i in range(len(chain)):
        model_name = chain[i]
        is_fallback = i > 0

        try:
            response = await call_openai(
                "/chat",
                model=model_name,
                messages=[
                    {"role": "system", "content": request["system_prompt"]},
                    *request["messages"],
                ],
                tools=request.get("tools"),
                stream=False,
                options={
                    "temperature": request.get("temperature", 0.1),
                    "num_predict": request.get("max_tokens", 1500),
                },
            )

            response.raise_for_status()

            resp_data = response.json()

            if is_fallback:
                logger.warning(
                    "Fallback model used",
                    correlation_id=request["correlation_id"],
                    primary_model=primary_model["name"],
                    fallback=model_name,
                )
            return {
                "content": resp_data["message"]["content"],
                "tool_calls": resp_data["message"].get("tool_calls", []),
                "model": model_name,
                "prompt_version": request.get("prompt_version", "1.0"),
                "tokens_used": {
                    "prompt": resp_data["prompt_eval_count"],
                    "completion": resp_data["eval_count"],
                    "total": resp_data["prompt_eval_count"] + resp_data["eval_count"],
                },
                "cost_usd": 0.0,
                "latency_secs": 0,
                "fallback_used": is_fallback,
            }
        except Exception:
            logger.exception(
                f"Model {model_name} failed",
                correlation_id=request["correlation_id"],
                error=str(Exception),
                is_last_fallback=(i == len(chain) - 1),
            )

            if i == len(chain) - 1:
                raise  # All models failed
            # Try next model in chain

    raise RuntimeError("All models in fallback chain failed")


def calculate_cost(model_name: str, usage: _TokensUsed) -> float:
    """Calculates the cost of a request based on the model used and tokens consumed."""
    model = MODELS.get(model_name)
    if not model:
        return 0.0

    input_cost = (usage["prompt"] / 1_000_000) * model["cost_per_million_input"]
    output_cost = (usage["completion"] / 1_000_000) * model["cost_per_million_output"]
    return input_cost + output_cost


MONTHLY_BUDGET: dict[str, float] = {
    "free": 1.00,
    "pro": 20.00,
    "enterprise": 200.00,
}


async def enforce_budget(user_id: UUID) -> None:
    """Checks if the user has exceeded their monthly budget."""
    user = await User.get_or_none(id=user_id).only("tier")

    budget = MONTHLY_BUDGET[user.tier if user else "free"]

    # Sum this month's AI costs
    start_of_month = datetime.now(UTC).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    result = await (
        UsageLog.filter(
            user_id=user_id,
            action__in=["chat", "agent_run", "document_ingested"],
            created_at__gte=start_of_month,
        )
        .annotate(total_cost=Sum("cost_usd"))
        .first()
        .values("total_cost")
    )

    spent = result["total_cost"] if result else 0.0

    if spent >= budget:
        error_response(429, f"Monthly AI budget exhausted (${spent:.2f}/${budget:.2f})")

    # Warn at 80%
    if spent >= budget * 0.8:
        logger.warning(
            "User approaching budget limit",
            user_id=user_id,
            spent=round(spent, 4),
            budget=round(budget, 2),
            percent_used=round((spent / budget) * 100, 1),
        )


async def track_cost(user_id: UUID, cost_usd: float) -> None:
    """Tracks the cost of a request in the UsageLog."""
    # Atomic increment in Redis for fast budget checks
    month_key = f"budget:{user_id}:{datetime.now(UTC).isoformat()[:7]}"
    await cache_incr_float(month_key, cost_usd)

    # Set expiry: auto-cleanup after the month ends
    days_left = days_remaining_in_month()
    await cache_expire(month_key, (days_left + 1) * 86400)


def days_remaining_in_month() -> int:
    """Returns the number of days remaining in the current month."""
    now = datetime.now(UTC)
    last_day = datetime(year=now.year, month=now.month + 1, day=1, tzinfo=UTC)
    return (last_day - now).days


class _AuditData(TypedDict):
    user_id: UUID
    correlation_id: str
    task_type: TaskType
    model: str
    prompt_version: str
    messages: list[_Message]
    cost_usd: float
    latency_secs: float
    fallback_used: NotRequired[bool]
    response: NotRequired[str]


async def audit_log(data: _AuditData) -> None:
    """Creates an audit log entry for an AI request."""
    try:
        input_text = "\n".join(
            f"[${m['role']}]: ${m['content']}" for m in data["messages"]
        )

        await AIAuditLog.create(
            user_id=data["user_id"],
            correlation_id=data["correlation_id"],
            task_type=data["task_type"],
            model=data["model"],
            prompt_version=data["prompt_version"],
            input_tokens=0,
            output_tokens=0,
            cost_usd=data["cost_usd"],
            latency_secs=data["latency_secs"],
            fallback_used=data.get("fallback_used", False),
            input_data=input_text[:500],  # Store first 500 chars to avoid PII
            output_data=data.get("response", "")[:500],  # Store first 500 chars
        )

    except Exception:
        # Audit logging should never crash the request
        logger.error(
            "Audit Log failed",
            error=str(Exception),
            correlation_id=data["correlation_id"],
        )
