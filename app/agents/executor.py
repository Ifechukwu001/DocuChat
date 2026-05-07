import json
from uuid import UUID
from typing import Any, Literal, TypedDict, NotRequired
from datetime import UTC, datetime

from app.lib.events import APP_EVENTS
from app.lib.logging import logger
from app.events.agent import AgentEvents
from app.config.prompts import AGENT_SYSTEM_PROMPT
from app.agents.tools.registry import TOOL_REGISTRY, get_tool_schemas
from app.lib.http.openai_breaker import call_openai


class AgentConfig(TypedDict, total=False):
    """Configuration for the agent's behavior and capabilities."""

    max_iterations: int
    timeout_secs: int
    cost_ceiling_usd: float
    model: str


TerminationReason = Literal[
    "completed", "iteration_limit", "timeout", "cost_limit", "error"
]


class AgentResult(TypedDict):
    """Result of executing an agent, including success status, final answer, and any relevant metadata."""

    answer: str
    sources: list[str]
    confidence: str
    iterations: int
    total_cost_usd: float
    termination_reason: TerminationReason
    trace: list[TraceStep]


class TraceStep(TypedDict):
    """Represents a single step in the agent's execution trace, including the tool called, input parameters, and tool output."""

    step: int
    phase: Literal["think", "act", "observe"]
    tool: NotRequired[str]
    input: NotRequired[Any]
    output: NotRequired[Any]
    duration_secs: float
    cost_usd: float


DEFAULT_CONFIG: AgentConfig = {
    "max_iterations": 10,
    "timeout_secs": 1800,
    "cost_ceiling_usd": 0.50,
    "model": "qwen2.5",
}


async def run_agent(
    question: str,
    user_id: UUID,
    correlation_id: str,
    config: AgentConfig = AgentConfig(),
) -> AgentResult:
    """Main function to execute the agent with the given question and configuration."""
    config = {**DEFAULT_CONFIG, **config}  # Merge default config with any overrides

    trace: list[TraceStep] = []
    total_cost_usd = 0
    iteration = 0
    start_time = datetime.now(UTC)

    # Build the conversation with LLM
    messages: list[dict[str, str]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_schemas = get_tool_schemas()

    logger.info(
        "Agent started",
        {
            "correlation_id": correlation_id,
            "question": question[:100],
            "max_iterations": config.get("max_iterations"),
            "cost_ceiling": config.get("cost_ceiling_usd"),
        },
    )

    while iteration < config.get("max_iterations", 10):
        # ── CHECK TIMEOUT ──
        elapsed = datetime.now(UTC) - start_time
        if elapsed.total_seconds() > config.get("timeout_secs", 60):
            logger.warn(
                "Agent timeout",
                correlation_id=correlation_id,
                iteration=iteration,
                elapsed=elapsed,
            )
            b_result = build_result("timeout", trace, total_cost_usd, iteration)

            APP_EVENTS.emit(
                AgentEvents.AGENT_COMPLETED,
                user_id=user_id,
                correlation_id=correlation_id,
                iterations=b_result["iterations"],
                total_cost_usd=b_result["total_cost_usd"],
                termination_reason=b_result["termination_reason"],
                tools_used=[s["tool"] for s in b_result["trace"] if "tool" in s],
                confidence=b_result["confidence"],
                duration_secs=(datetime.now(UTC) - start_time).total_seconds(),
            )

            return b_result

        #  ── CHECK COST ──
        if total_cost_usd > config.get("cost_ceiling_usd", 0.50):
            logger.warn(
                "Agent cost ceiling hit",
                correlation_id=correlation_id,
                iteration=iteration,
                total_cost_usd=total_cost_usd,
            )
            b_result = build_result("cost_limit", trace, total_cost_usd, iteration)

            APP_EVENTS.emit(
                AgentEvents.AGENT_COMPLETED,
                user_id=user_id,
                correlation_id=correlation_id,
                iterations=b_result["iterations"],
                total_cost_usd=b_result["total_cost_usd"],
                termination_reason=b_result["termination_reason"],
                tools_used=[s["tool"] for s in b_result["trace"] if "tool" in s],
                confidence=b_result["confidence"],
                duration_secs=(datetime.now(UTC) - start_time).total_seconds(),
            )
            return b_result

        iteration += 1
        step_start = datetime.now(UTC)

        # ── THINK: Ask the model what to do ──
        response = await call_openai(
            "/chat",
            model=config.get("model", "qwen2.5"),
            messages=messages,
            tools=tool_schemas,
            stream=False,
            options={"temperature": 0.1},
        )

        logger.critical(
            "Agent model response",
            correlation_id=correlation_id,
            iteration=iteration,
            response=response.text,
        )

        data = response.json()
        prompt_tokens = data["prompt_eval_count"]
        completion_tokens = data["eval_count"]

        step_cost = (
            (prompt_tokens / 1_000_000) * 2.50  # Input cost
            + (completion_tokens / 1_000_000) * 10.00  # Output cost
        )
        total_cost_usd += step_cost

        assistant_message = {
            "role": data["message"]["role"],
            "content": data["message"]["content"],
        }

        # Add the assistant's response to conversation
        messages.append(assistant_message)

        # ── NO TOOL CALL: Model wants to respond directly ──
        if (
            "tool_calls" not in data["message"]
            or len(data["message"]["tool_calls"]) == 0
        ):
            trace.append(
                {
                    "step": iteration,
                    "phase": "think",
                    "output": data["message"]["content"],
                    "duration_secs": (datetime.now(UTC) - step_start).total_seconds(),
                    "cost_usd": step_cost,
                }
            )

            # Treat direct response as final answer
            b_result: AgentResult = {
                "answer": data["message"]["content"],
                "sources": [],
                "confidence": "medium",
                "iterations": iteration,
                "total_cost_usd": total_cost_usd,
                "termination_reason": "completed",
                "trace": trace,
            }

            APP_EVENTS.emit(
                AgentEvents.AGENT_COMPLETED,
                user_id=user_id,
                correlation_id=correlation_id,
                iterations=b_result["iterations"],
                total_cost_usd=b_result["total_cost_usd"],
                termination_reason=b_result["termination_reason"],
                tools_used=[s["tool"] for s in b_result["trace"] if "tool" in s],
                confidence=b_result["confidence"],
                duration_secs=(datetime.now(UTC) - start_time).total_seconds(),
            )
            return b_result

        # ── ACT: Execute each tool call ──
        for tool_call in data["message"]["tool_calls"]:
            tool_id = tool_call["id"]
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            logger.info(
                "Agent tool call",
                correlation_id=correlation_id,
                iteration=iteration,
                tool=tool_name,
                args=tool_args,
            )

            # Validate: is this tool in the registry?
            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                error_result = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"Error: unknown tool '{tool_name}'",
                }

                messages.append(error_result)
                trace.append(
                    {
                        "step": iteration,
                        "phase": "act",
                        "tool": tool_name,
                        "input": tool_args,
                        "output": {"error": "Unknown tool"},
                        "duration_secs": (
                            datetime.now(UTC) - step_start
                        ).total_seconds(),
                        "cost_usd": step_cost,
                    }
                )
                continue

            # Check for final answer
            if tool_name == "final_answer":
                trace.append(
                    {
                        "step": iteration,
                        "phase": "act",
                        "tool": tool_name,
                        "input": tool_args,
                        "duration_secs": (
                            datetime.now(UTC) - step_start
                        ).total_seconds(),
                        "cost_usd": step_cost,
                    }
                )

                b_result: AgentResult = {
                    "answer": tool_args["answer"],
                    "sources": tool_args.get("sources", []),
                    "confidence": tool_args.get("confidence", "medium"),
                    "iterations": iteration,
                    "total_cost_usd": total_cost_usd,
                    "termination_reason": "completed",
                    "trace": trace,
                }

                APP_EVENTS.emit(
                    AgentEvents.AGENT_COMPLETED,
                    user_id=user_id,
                    correlation_id=correlation_id,
                    iterations=b_result["iterations"],
                    total_cost_usd=b_result["total_cost_usd"],
                    termination_reason=b_result["termination_reason"],
                    tools_used=[s["tool"] for s in b_result["trace"] if "tool" in s],
                    confidence=b_result["confidence"],
                    duration_secs=(datetime.now(UTC) - start_time).total_seconds(),
                )
                return b_result

            # Validate inputs
            try:
                validation = tool["parameters"].model_validate(tool_args)
            except Exception as e:
                error_result = {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"Validation error: {e}",
                }

                messages.append(error_result)
                trace.append(
                    {
                        "step": iteration,
                        "phase": "act",
                        "tool": tool_name,
                        "input": tool_args,
                        "output": {"error": "Invalid arguments"},
                        "duration_secs": (
                            datetime.now(UTC) - step_start
                        ).total_seconds(),
                        "cost_usd": step_cost,
                    }
                )
                continue

            # Execute the tool
            try:
                result = await tool["handler"](
                    {"user_id": user_id, "correlation_id": correlation_id},
                    **validation.model_dump(),
                )

                # ── OBSERVE: Feed result back to the model ──
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(result["data"]),
                    }
                )

                trace.append(
                    {
                        "step": iteration,
                        "phase": "observe",
                        "tool": tool_name,
                        "input": tool_args,
                        "output": result["data"],
                        "duration_secs": (
                            datetime.now(UTC) - step_start
                        ).total_seconds(),
                        "cost_usd": step_cost,
                    }
                )
            except Exception as e:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": f"Tool error:: {e}",
                    }
                )
                trace.append(
                    {
                        "step": iteration,
                        "phase": "observe",
                        "tool": tool_name,
                        "input": tool_args,
                        "output": {"error": str(e)},
                        "duration_secs": (
                            datetime.now(UTC) - step_start
                        ).total_seconds(),
                        "cost_usd": step_cost,
                    }
                )
    # Iteration limit reached
    logger.warn(
        "Agent iteration limit",
        correlation_id=correlation_id,
        iterations=iteration,
        total_cost_usd=total_cost_usd,
    )
    b_result = build_result("iteration_limit", trace, total_cost_usd, iteration)

    APP_EVENTS.emit(
        AgentEvents.AGENT_COMPLETED,
        user_id=user_id,
        correlation_id=correlation_id,
        iterations=b_result["iterations"],
        total_cost_usd=b_result["total_cost_usd"],
        termination_reason=b_result["termination_reason"],
        tools_used=[s["tool"] for s in b_result["trace"] if "tool" in s],
        confidence=b_result["confidence"],
        duration_secs=(datetime.now(UTC) - start_time).total_seconds(),
    )

    return b_result


def build_result(
    reason: TerminationReason,
    trace: list[TraceStep],
    cost_usd: float,
    iterations: int,
) -> AgentResult:
    """Helper function to build the final AgentResult based on termination reason."""
    # Try to extract a partial answer from the trace
    last_observe = next(
        (
            o
            for o in reversed(trace.copy())
            if o["phase"] == "observe" and "output" in o
        ),
        None,
    )
    return {
        "answer": f"I was unable to complete my analysis ({reason}). "
        + "Here is what I found so far: "
        + json.dumps(last_observe["output"])
        if last_observe
        else "No partial results are available.",
        "sources": [],
        "confidence": "low",
        "iterations": iterations,
        "total_cost_usd": cost_usd,
        "termination_reason": reason,
        "trace": trace,
    }
