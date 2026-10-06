# Billing & Payment Service

Микросервис управления лицевыми счетами, счетами-фактурами и платежами
в составе экосистемы «Умный город».

## Стек

FastAPI · PostgreSQL · SQLAlchemy 2.0 · Pydantic v2 · python-jose (JWT) ·
httpx (межсервисные вызовы) · Docker / Docker Compose

## Архитектурные решения

- **Собственная БД** `billing_db`, никаких прямых соединений с БД других сервисов.
- **Аутентификация**: JWT, выданный Identity & Auth Service, проверяется локально
  по общему секрету (`BILLING_JWT_SECRET`) — без похода в сеть на каждый запрос.
  Для действий, требующих существования пользователя (создание счёта), сервис
  может дополнительно обратиться к `GET /users/{id}` Identity Service
  (см. `app/clients/identity_client.py`).
- **Webhook провайдера** (`POST /payments/webhook/success`) защищён отдельным
  общим секретом (заголовок `X-Webhook-Secret`), а не пользовательским JWT —
  это серверный межсервисный вызов. Обработка идемпотентна: повторный вебхук
  по уже завершённому платежу не меняет состояние повторно.
- **Нотификации**: после успешной оплаты сервис асинхронно вызывает
  Notification Service. Сбой отправки уведомления **не** откатывает платёж —
  ошибка только логируется.
- **Логирование**: middleware логирует каждый запрос (метод, путь, статус,
  время выполнения), плюс точечные логи ключевых бизнес-событий (создание
  счёта, платежа, обработка вебхука).
- **Обработка ошибок**: 401 (нет/невалиден токен), 403 (чужие данные),
  404 (счёт/платёж не найден), 409 (повторная оплата, счёт отменён),
  422 (ошибка валидации Pydantic), 502 (недоступен Identity Service),
  500 (ошибка БД) — везде возвращается JSON `{"detail": "..."}`.

## Endpoints

| Метод | Путь                                | Назначение                                      | Доступ                  |
|-------|--------------------------------------|--------------------------------------------------|-------------------------|
| GET   | `/accounts/{userId}/invoices`        | Список счетов пользователя                       | сам пользователь / admin / operator |
| POST  | `/accounts`                          | Создание лицевого счёта                          | сам пользователь / admin / operator |
| POST  | `/accounts/{userId}/invoices`        | Выставление счёта (напр. из Utility Service)      | admin / operator        |
| POST  | `/payments`                          | Инициирование оплаты счёта                        | владелец счёта / admin  |
| POST  | `/payments/webhook/success`          | Коллбэк от платёжного провайдера                  | webhook-секрет          |
| GET   | `/health`                            | Проверка живости сервиса                          | public                  |

Полная интерактивная документация (OpenAPI/Swagger) доступна на `/docs`,
спецификация — на `/openapi.json`.

## Запуск локально

```bash
cp .env.example .env
# при необходимости поправьте секреты в .env
docker compose up --build
```

Сервис будет доступен на `http://localhost:8003`, Swagger UI — на
`http://localhost:8003/docs`.

## Пример сценария

```bash
# 1. Оператор выставляет счёт пользователю (JWT оператора в $OPERATOR_TOKEN)
curl -X POST http://localhost:8003/accounts/<userId>/invoices \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1500.00, "description": "Вывоз мусора, сентябрь", "due_date": "2026-10-20"}'

# 2. Пользователь инициирует оплату (JWT пользователя в $USER_TOKEN)
curl -X POST http://localhost:8003/payments \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "<invoiceId>", "method": "card"}'

# 3. Платёжный провайдер подтверждает оплату вебхуком
curl -X POST http://localhost:8003/payments/webhook/success \
  -H "X-Webhook-Secret: webhook-secret-change-me" \
  -H "Content-Type: application/json" \
  -d '{"provider_ref": "sim_xxx", "status": "succeeded", "amount": 1500.00}'
```

## Структура проекта

```
billing-payment-service/
├── app/
│   ├── main.py                 — точка входа, middleware, обработчики ошибок
│   ├── config.py                — настройки из переменных окружения
│   ├── database.py              — SQLAlchemy engine/session
│   ├── models.py                — ORM-модели (Account, Invoice, Payment, WebhookEvent)
│   ├── schemas.py                — Pydantic-схемы запросов/ответов
│   ├── auth.py                   — проверка JWT, авторизация по ролям
│   ├── logging_config.py         — настройка логирования
│   ├── clients/
│   │   ├── identity_client.py    — вызовы Identity & Auth Service
│   │   └── notification_client.py — вызовы Notification Service
│   └── routers/
│       ├── accounts.py           — /accounts, /accounts/{userId}/invoices
│       └── payments.py           — /payments, /payments/webhook/success
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```
