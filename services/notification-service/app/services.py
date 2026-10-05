import logging

logger = logging.getLogger(__name__)


def render_template(template_str: str, data: dict) -> str:
    if not template_str:
        return ""
    result = template_str
    for key, value in (data or {}).items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def send_via_provider(channel: str, user_id: str, title: str, message: str) -> None:

    logger.info("=== SENDING %s ===", channel.upper())
    logger.info("To user: %s", user_id)
    logger.info("Title:   %s", title)
    logger.info("Message: %s", message)
    logger.info("===================")