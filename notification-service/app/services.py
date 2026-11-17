import logging
import re

log = logging.getLogger("notification")

# Шаблоны, которые используют остальные сервисы «Умного города».
DEFAULT_TEMPLATES = [
    ("PAYMENT_SUCCESS", "Платёж прошёл успешно", "Ваш платёж на сумму {{amount}} руб. успешно обработан."),
    ("ISSUE_CREATED", "Заявка принята", "Ваша заявка №{{issue_id}} по адресу {{address}} принята в работу."),
    ("ISSUE_STATUS_CHANGED", "Статус заявки изменён", "Статус вашей заявки №{{issue_id}} изменён на «{{status}}»."),
    ("PARKING_RESERVED", "Парковка забронирована", "Место на парковке «{{parking_name}}» забронировано до {{end_time}}."),
    (
        "SENSOR_ALERT",
        "Превышение порога: {{sensor_name}}",
        "Датчик «{{sensor_name}}» ({{location}}): показание {{value}}. {{alert}}",
    ),
]


def render_template(template: str | None, data: dict) -> str:
    """Подставляет {{key}}; незаполненные плейсхолдеры остаются как есть."""
    if not template:
        return ""
    return re.sub(
        r"\{\{\s*(\w+)\s*\}\}",
        lambda m: str(data[m.group(1)]) if m.group(1) in data else m.group(0),
        template,
    )


def send_via_provider(channel: str, user_id: int, title: str, message: str) -> None:
    """Заглушка внешнего провайдера (email/SMS/push): пишет в лог."""
    log.info("=== SENDING %s to user %s === %s | %s", channel.upper(), user_id, title, message)
