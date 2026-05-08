from tortoise import Tortoise, run_async  # type: ignore

from app.orm.config import TORTOISE_CONFIG
from app.orm.models import PromptTemplate
from app.lib.logging import logger
from app.config.prompts import RAG_SYSTEM_PROMPT, AGENT_SYSTEM_PROMPT


async def main() -> None:
    """Script entrypoint."""
    await Tortoise.init(config=TORTOISE_CONFIG)

    await PromptTemplate.get_or_create(  # type: ignore
        task_type="chat",
        version="v1",
        defaults={
            "task_type": "chat",
            "version": "v1",
            "name": "RAG Chat - Initial",
            "content": RAG_SYSTEM_PROMPT,
            "is_active": True,
        },
    )

    await PromptTemplate.get_or_create(  # type: ignore
        task_type="agent",
        version="v1",
        defaults={
            "task_type": "agent",
            "version": "v1",
            "name": "Research Agent - Initial",
            "content": AGENT_SYSTEM_PROMPT,
            "is_active": True,
        },
    )

    logger.info("Prompt templates seeded: 2 templates")


if __name__ == "__main__":
    run_async(main())
