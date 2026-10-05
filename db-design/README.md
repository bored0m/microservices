# Проектирование баз данных — «Умный город»

## Принцип: Database per Service

Каждый микросервис владеет **собственной изолированной базой** PostgreSQL.
Прямые SQL-соединения между базами разных сервисов запрещены.
Если сервису А нужны данные сервиса Б — он делает HTTP-запрос к API сервиса Б.

Поэтому все "внешние ключи" на пользователя (`user_id`) в БД Transport,
Utility, Environment, Billing и Notification — это **логические ссылки без
физического FOREIGN KEY** на таблицу `users` (та живёт в другой базе).
Целостность таких ссылок обеспечивается на уровне приложения — сервис
проверяет существование пользователя вызовом `GET /users/{id}` к
Identity & Auth Service.

## Карта баз данных

| Сервис               | База данных         | Ключевые таблицы                                              |
|-----------------------|----------------------|----------------------------------------------------------------|
| Identity & Auth        | `identity_db`        | users, auth_tokens                                             |
| Transport              | `transport_db`       | vehicles, parking_lots, parking_reservations                   |
| Utility                | `utility_db`         | issues, issue_status_history                                   |
| Environment             | `environment_db`     | sensors, sensor_data                                            |
| Billing & Payment       | `billing_db`         | accounts, invoices, payments, payment_webhook_events            |
| Notification            | `notification_db`    | notifications, notification_templates                          |

## ER-диаграммы (Mermaid)

### Identity & Auth Service
```mermaid
erDiagram
    USERS ||--o{ AUTH_TOKENS : has
    USERS {
        uuid id PK
        varchar email UK
        varchar hashed_password
        varchar full_name
        varchar phone
        enum role
        bool is_active
        timestamptz created_at
    }
    AUTH_TOKENS {
        uuid id PK
        uuid user_id FK
        varchar token_hash
        timestamptz expires_at
        bool revoked
    }
```

### Transport Service
```mermaid
erDiagram
    PARKING_LOTS ||--o{ PARKING_RESERVATIONS : has
    VEHICLES {
        uuid id PK
        enum type
        varchar plate
        float latitude
        float longitude
        enum status
    }
    PARKING_LOTS {
        uuid id PK
        varchar name
        int total_spots
        int available_spots
        numeric price_per_hour
    }
    PARKING_RESERVATIONS {
        uuid id PK
        uuid parking_id FK
        uuid reserved_by "ref: identity_db.users.id"
        timestamptz start_time
        timestamptz end_time
        enum status
    }
```

### Utility Service
```mermaid
erDiagram
    ISSUES ||--o{ ISSUE_STATUS_HISTORY : has
    ISSUES {
        uuid id PK
        uuid user_id "ref: identity_db.users.id"
        enum category
        text description
        enum status
        uuid assigned_to "ref: identity_db.users.id"
    }
    ISSUE_STATUS_HISTORY {
        uuid id PK
        uuid issue_id FK
        enum old_status
        enum new_status
        uuid changed_by "ref: identity_db.users.id"
    }
```

### Environment Service
```mermaid
erDiagram
    SENSORS ||--o{ SENSOR_DATA : produces
    SENSORS {
        uuid id PK
        enum type
        float latitude
        float longitude
        enum status
    }
    SENSOR_DATA {
        bigint id PK
        uuid sensor_id FK
        varchar metric_name
        numeric value
        varchar unit
        timestamptz recorded_at
    }
```

### Billing & Payment Service
```mermaid
erDiagram
    ACCOUNTS ||--o{ INVOICES : has
    INVOICES ||--o{ PAYMENTS : has
    PAYMENTS ||--o{ PAYMENT_WEBHOOK_EVENTS : logs
    ACCOUNTS {
        uuid id PK
        uuid user_id "ref: identity_db.users.id"
        numeric balance
    }
    INVOICES {
        uuid id PK
        uuid account_id FK
        numeric amount
        enum status
        date due_date
    }
    PAYMENTS {
        uuid id PK
        uuid invoice_id FK
        numeric amount
        enum method
        enum status
        varchar provider_ref
    }
    PAYMENT_WEBHOOK_EVENTS {
        uuid id PK
        uuid payment_id FK
        varchar event_type
        jsonb raw_payload
    }
```

### Notification Service
```mermaid
erDiagram
    NOTIFICATION_TEMPLATES ||--o{ NOTIFICATIONS : "used by (logical)"
    NOTIFICATIONS {
        uuid id PK
        uuid user_id "ref: identity_db.users.id"
        varchar source_service
        enum channel
        enum status
        timestamptz sent_at
    }
    NOTIFICATION_TEMPLATES {
        uuid id PK
        varchar code UK
        varchar subject_template
        text body_template
    }
```

## Межсервисные зависимости (кто кого вызывает по HTTP)

```mermaid
graph LR
    Transport -->|GET /users/id| Identity
    Utility -->|GET /users/id| Identity
    Utility -->|POST /notifications| Notification
    Billing -->|GET /users/id| Identity
    Billing -->|POST /notifications| Notification
    Environment -->|POST /notifications, при превышении порога| Notification
    Transport -->|POST /notifications, подтверждение брони| Notification
```

## Обоснование выбора типов и ограничений

- **UUID вместо SERIAL** для первичных ключей сущностей, которыми обмениваются
  сервисы (`users.id`, `issues.id`, `vehicles.id` и т.д.) — исключает угадывание
  идентификаторов и коллизии при распределённой генерации.
- **ENUM-типы** для статусов (`issue_status`, `payment_status` и т.п.) — валидация
  на уровне БД плюс самодокументируемость схемы.
- **CHECK-ограничения** (например, `end_time > start_time`, `amount > 0`) —
  защита от некорректных данных ещё до попадания в бизнес-логику.
- **JSONB** в `payment_webhook_events.raw_payload` — гибкое хранение сырых
  вебхуков от внешнего платёжного провайдера без потери данных для аудита.
- Каждая таблица с изменяемым состоянием имеет `created_at`/`updated_at`
  (или отдельную таблицу истории, как `issue_status_history`) для аудита.

## Файлы архива

```
db-design/
├── README.md                      (этот файл + ER-диаграммы)
├── identity-auth/schema.sql
├── transport/schema.sql
├── utility/schema.sql
├── environment/schema.sql
├── billing-payment/schema.sql
└── notification/schema.sql
```
