# Экосистема микросервисов "Умный город"

Распределенная система управления городской инфраструктурой «Умный город». Состоит из шести независимых backend-микросервисов на FastAPI, взаимодействующих через REST API, одного SPA-фронтенда на React и шести отдельных баз данных PostgreSQL. Каждый сервис изолирован: своя БД, свой контейнер, свой Swagger.

## Возможности

- **Регистрация и аутентификация** по email/паролю, JWT-токены (HS256), роли `resident` и `admin`.
- **Заявки ЖКХ**: подача, категоризация, смена статуса администратором, фильтрация по статусу.
- **Биллинг**: лицевые счета, счета-фактуры, оплата картой/переводом/кошельком, вебхуки платёжного провайдера с проверкой HMAC-секрета, идемпотентность.
- **Транспорт и парковки**: справочник транспорта, парковочные места, бронирование с контролем свободных мест, отмена с возвратом места.
- **Экология**: датчики воздуха/шума/температуры/воды/радиации, история показаний, пороговые оповещения администраторам.
- **Уведомления**: централизованная отправка через шаблоны (`PAYMENT_SUCCESS`, `ISSUE_CREATED`, `ISSUE_STATUS_CHANGED`, `PARKING_RESERVED`, `SENSOR_ALERT`), журнал доставки.
- **Единый веб-интерфейс**: вкладка на каждый сервис, авторизация через Auth, дашборд состояния `/health` всех сервисов.

---
# Разработка
## Стек

| Слой | Технологии |
|---|---|
| **Backend** | Python 3.12, FastAPI 0.115, Pydantic 2.10, SQLAlchemy 2.0, PyJWT, bcrypt, httpx |
| **БД** | PostgreSQL 16 |
| **Frontend** | React 18, Vite 5, JSX, CSS |
| **Инфраструктура** | Docker, Docker Compose, Uvicorn |

## Микросервисы

| Сервис | Порт | БД | Swagger |
|---|---|---|---|
| **Identity & Auth** | 8001 | auth-db | http://localhost:8001/docs |
| **Utility** | 8002 | utility-db | http://localhost:8002/docs |
| **Billing & Payment** | 8003 | billing-db | http://localhost:8003/docs |
| **Notification** | 8004 | notification-db | http://localhost:8004/docs |
| **Transport** | 8005 | transport-db | http://localhost:8005/docs |
| **Environment** | 8006 | environment-db | http://localhost:8006/docs |
| **Frontend** | 3000 | — | http://localhost:3000 |

### Identity & Auth

Сервис аутентификации и профилей. Хранит пользователей (`email`, `username`, `password_hash`, `role`), выдаёт JWT, подтверждает токены для остальных сервисов.

- `POST /auth/register` — регистрация, роль `admin` присваивается, если email входит в `ADMIN_EMAILS`, иначе `resident`.
- `POST /auth/login` — выдача `access_token` (HS256, время жизни `JWT_EXPIRE_MINUTES`).
- `GET /users/me` — данные текущего пользователя (используется всеми сервисами для валидации токена).
- `GET /users`, `GET /users/{id}` — список и карточка пользователя (для авторизованных).
- Пароли хешируются bcrypt.

### Utility

Заявки ЖКХ. Категории: `water`, `heating`, `electricity`, `elevator`, `cleaning`, `other`. Статусы: `new`, `in_progress`, `resolved`, `rejected`.

- `POST /issues` — создать заявку (автор берётся из токена; рассылается `ISSUE_CREATED`).
- `GET /issues?status=` — свои заявки; admin видит все. Фильтр по статусу.
- `PUT /issues/{id}` — смена статуса (только admin); при смене — `ISSUE_STATUS_CHANGED`.

### Billing & Payment

Лицевые счета, счета-фактуры, платежи.

- `GET /accounts/{userId}/invoices` — счета пользователя (свои; admin — любого).
- `POST /accounts` — создать лицевой счёт (admin или сам пользователь).
- `POST /accounts/{userId}/invoices` — выставить счёт (только admin).
- `POST /payments` — инициировать оплату по счёту. В `BILLING_SIMULATE_PAYMENT_SUCCESS=true` платёж сразу помечается успешным и отправляется `PAYMENT_SUCCESS` в Notification.
- `POST /payments/webhook/success` — коллбэк провайдера (проверка `X-Webhook-Secret`, идемпотентность, лог в `payment_webhook_events`).

### Transport

Городской транспорт и парковки. Типы ТС: `bus`, `tram`, `shuttle`, `municipal_car`. Статусы: `active`, `idle`, `maintenance`, `offline`.

- `GET /vehicles`, `GET /parking` — для всех пользователей.
- **admin:** `POST/PATCH/DELETE /vehicles`, `POST/DELETE /parking` (нельзя удалить парковку с активными бронями).
- `POST /parking/{id}/reserve` — бронь (с `SELECT ... FOR UPDATE`, декремент свободных мест, `PARKING_RESERVED`).
- `GET /parking/reservations` — свои (admin — все); `POST /parking/reservations/{id}/cancel` — отмена с возвратом места.

### Environment

Экологические датчики. Типы: `air_quality`, `noise`, `temperature`, `water_quality`, `radiation`. Пороги: воздух `100`, шум `85`, температура `50`.

- `GET /sensors` — датчики с последним показанием и порогом.
- `GET /sensors/{id}/data?limit=` — история показаний.
- **admin:** `POST /sensors`, `PATCH /sensors/{id}` (статус), `DELETE /sensors/{id}` (с историей), `POST /sensors/data` — передать показание. При превышении порога **всем admin** уходит `SENSOR_ALERT` (список admin запрашивается в Auth).

### Notification

Централизованная отправка и хранение уведомлений. Каналы: `email`, `sms`, `push`, `in_app`. Статусы: `queued`, `sent`, `failed`.

- `POST /notifications` — **внутренний** вызов от других сервисов (без токена). Принимает либо `template_code` + `template_data`, либо готовые `title` + `message`. Рендер шаблона `{{key}}` → значение.
- `GET /notifications?user_id=&limit=` — свои (admin может смотреть чужого).
- `GET /templates` — список шаблонов.
- При старте сервис создаёт таблицы и заполняет дефолтные шаблоны (`PAYMENT_SUCCESS`, `ISSUE_CREATED`, `ISSUE_STATUS_CHANGED`, `PARKING_RESERVED`, `SENSOR_ALERT`).
- Провайдер отправки — заглушка, пишет в лог. Ошибка отправки не откатывает бизнес-операции других сервисов.

### Frontend

SPA на React + Vite, hash-роутинг (`/#profile`, `/#issues`, `/#billing`, `/#transport`, `/#environment`, `/#notifications`).

- **Авторизация** через Auth, токен хранится в `localStorage`.
- **Вкладка «Сервисы»** — проверяет `/health` каждого микросервиса, показывает статус и ссылки на Swagger.
- **Профиль** — данные пользователя; список пользователей только для admin.
- **Заявки ЖКХ** — создание, фильтр по статусу; admin может менять статус.
- **Счета и оплата** — admin выставляет счёт, житель оплачивает.
- **Транспорт** — бронь места, admin управляет транспортом и парковками.
- **Экология** — датчики, история, статусы; показания передаёт admin.
- **Уведомления** — свои; admin может смотреть по `user_id`.

URL-ы сервисов передаются на этапе сборки через `VITE_*` build args (см. `docker-compose.yml`).

## Взаимодействие сервисов

- **Проверка токена.** Все сервисы (кроме Auth и Notification на входящих `POST /notifications`) используют зависимость `get_current_user`, которая делает `GET {AUTH_SERVICE_URL}/users/me` с `Authorization: Bearer <token>` через `httpx.AsyncClient`. Секрет JWT хранится **только** в Auth.
- **Уведомления.** Доменные сервисы (Utility, Billing, Transport, Environment) вызывают `POST {NOTIFICATION_SERVICE_URL}/notifications` — либо с `template_code`, либо с готовым текстом. Ошибка отправки логируется, но **не откатывает** бизнес-операцию (fire-and-forget).
- **Список администраторов.** Environment запрашивает `GET {AUTH}/users` с токеном того, кто передал показание, и шлёт `SENSOR_ALERT` всем `admin`. Если запрос не удался — уведомление уходит только этому пользователю.
- **Изоляция БД.** Каждый сервис имеет свою PostgreSQL. Ссылки на `user_id` хранятся как целые числа без внешних ключей (чужая БД).
- **Коды ошибок.** `401` — нет/невалидный токен; `403` — нет прав; `404` — не найдено; `409` — конфликт/дубликат; `422` — ошибка валидации; `503` — Auth Service недоступен; `502` — Auth вернул неожиданный ответ.

---
# Старт

## Требования 

- Docker ≥ 20.10 и Docker Compose v2 (docker compose)
- Cвободные порты: 3000, 8001–8006
- ~2 GB свободного места

## Шаги запуска
1. Клонирование репозитория 
```
git clone https://github.com/bored0m/microservices.git
cd microservices
```
2.  Собрать и запустить
```
docker compose up --build
```
Первая сборка занимает 2–5 минут (скачивание postgres:16-alpine, python:3.12-slim, node). При старте каждый сервис сам создаёт таблицы (Base.metadata.create_all), Notification дополнительно заполняет шаблоны.

3.  Дождаться готовности 

 В логах появятся строки вида auth запущен, таблицы БД проверены/созданы, а /health вернёт {"status":"ok"}.

4. Открыть приложение 
```
 http://localhost:3000
```

5. Остановка приложения
```
docker compose down            # остановить и удалить контейнеры (данные в volume сохраняются)
docker compose down -v         # удалить также volume с данными БД (полный сброс)
```

---
# Примеры запросов

## Регистрация и логин
```
curl -X POST http://localhost:8001/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"ivan@mail.ru","username":"ivan","password":"secret123"}'

TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ivan@mail.ru","password":"secret123"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

## Заявка ЖКХ
```
curl -X POST http://localhost:8002/issues \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Нет горячей воды","description":"Со вторника","category":"water","address":"ул. Ленина, 5"}'
```

## Бронь парковки
```
curl -X POST http://localhost:8005/parking/<PARKING_ID>/reserve \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"start_time":"2026-01-01T10:00:00Z","end_time":"2026-01-01T12:00:00Z"}'
```

## Показания датчиков
```
curl -X POST http://localhost:8006/sensors/data \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sensor_id":"<SENSOR_UUID>","value":120}'
```

---
# Особенности реализации

- **Без миграций.** Для учебного проекта таблицы создаются через Base.metadata.create_all при старте. В проде следует перейти на Alembic.

- **JWT только в Auth.** Остальные сервисы не знают секрета и валидируют токен через GET /users/me — это осознанный выбор в пользу изоляции.

- **Fire-and-forget уведомления.** Сбой Notification не ломает оплату/бронь/заявку — ошибка пишется в лог.

- **Идемпотентность вебхука.** Повторный успешный коллбэк возвращает already_processed и не дублирует списание/уведомление.

- **Гонки на парковке.** SELECT ... FOR UPDATE при бронировании и отмене защищает available_spaces от race condition.

- **CORS.** Во всех сервисах разрешён origin http://localhost:3000 (фронтенд). При деплое на другой домен — поменять в docker-compose.yml.

- **Swagger** доступен на каждом сервисе по /docs — удобно для ручной проверки.