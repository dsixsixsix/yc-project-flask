# Минимальный CRUD c Flask + SQLite + S3-совместимым Object Storage

## Структура проекта

Проект организован по модульному принципу для лучшей читаемости и поддержки:

```
app/
├── models/          # Модели БД (Role, User, Item)
├── routes/          # Маршруты (auth, iam, items, main)
├── services/        # Бизнес-логика (auth, storage)
├── utils/           # Утилиты (декораторы, обработчики ошибок)
└── templates/       # HTML шаблоны
```

Подробное описание структуры см. в [STRUCTURE.md](STRUCTURE.md)

## Что есть
- Framework: Flask.
- БД: SQLite (можно заменить через `DATABASE_URL`).
- Object Storage: S3-совместимый (MinIO/AWS). Файлы загружаются и URL сохраняется в таблицу.
- CRUD для сущности `Item`: `id`, `name`, `description`, `file_url`.
- Ролевая модель доступа (admin, user, guest) с IAM-сервисом.
- Балансировщик нагрузки (Nginx).
- Виртуальные сети (VPC) через Docker networks.
- **Terraform-спецификация** для развертывания всей инфраструктуры.

## Развертывание через Terraform

Вся инфраструктура описана Terraform-спецификацией в папке `terraform/`.

### Требования:
- Terraform (установи с https://www.terraform.io/downloads)
- Docker Desktop (для Docker provider)

### Быстрый старт с Terraform:

```bash
cd terraform

# Инициализация Terraform
terraform init

# Просмотр плана развертывания
terraform plan

# Развертывание инфраструктуры
terraform apply

# После развертывания создай тестовых пользователей
curl -X POST http://localhost:8080/init-test-users

# Удаление инфраструктуры
terraform destroy
```

Terraform создаст:
- 3 виртуальные сети (VPC): frontend, backend, storage
- Docker volumes для данных MinIO
- 3 контейнера: nginx (балансировщик), app (Flask), minio (Object Storage)
- Все зависимости и сетевые подключения

### Альтернатива: Docker Compose

Если предпочитаешь Docker Compose, используй инструкции ниже.

## Подготовка (для локального запуска без Docker)
1) Скопируй пример переменных:
```bash
cp env.example .env
```
2) Установи зависимости (желательно в venv):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3) Подними S3-совместимое хранилище. Для локального теста удобно MinIO:

**Вариант A: Через Docker (если установлен Docker Desktop)**
- Сначала запусти Docker Desktop приложение
- Затем выполни:
```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"
```

**Вариант B: Установка MinIO без Docker (macOS)**
```bash
# Установка через Homebrew
brew install minio/stable/minio

# Запуск MinIO
minio server ~/minio-data --console-address ":9001"
```
При первом запуске MinIO покажет логин и пароль (по умолчанию `minioadmin` / `minioadmin`).

**После запуска MinIO:**
- Открой веб-консоль: `http://localhost:9001`
- Войди с учетными данными (по умолчанию `minioadmin` / `minioadmin`)
- Создай bucket `demo-bucket` через веб-интерфейс

## Запуск
```bash
flask --app app run --debug
```
Приложение автоматически создаст таблицу `items` в SQLite.

### Запуск через Docker Compose (альтернатива Terraform)

**Примечание:** Для production рекомендуется использовать Terraform (см. выше).

Локальный аналог варианта с балансировщиком нагрузки:

```bash
docker compose up --build
```

Что поднимается:
- `app` — контейнер с Flask-приложением на порту `7777` (внутри сети Docker).
- `minio` — Object Storage, доступен с хоста:
  - API: `http://localhost:9000`
  - Консоль: `http://localhost:9001`
- `nginx` — балансировщик/реверс-прокси:
  - Принимает HTTP на `http://localhost:8080`
  - Проксирует трафик на сервис `app:7777`

### Виртуальные сети (VPC)

Решение использует несколько изолированных Docker networks, эмулирующих виртуальные сети Yandex Cloud:

- **frontend-network** (172.20.0.0/24) — публичная подсеть для балансировщика nginx
- **backend-network** (172.21.0.0/24) — внутренняя подсеть для backend-сервисов (app, minio)
- **storage-network** (172.22.0.0/24) — подсеть для storage-сервисов

Сервисы изолированы по сетям:
- `nginx` подключён к `frontend-network` и `backend-network` (может принимать внешние запросы и обращаться к backend)
- `app` подключён только к `backend-network` (изолирован от внешнего доступа)
- `minio` подключён к `backend-network` и `storage-network` (доступен из backend, но изолирован в storage-подсети)

Это обеспечивает сетевую изоляцию и безопасность, аналогично VPC в Yandex Cloud.

Таким образом, для проверки CRUD через браузер в docker-режиме используй:
- UI: `http://localhost:8080/`
- MinIO-консоль: `http://localhost:9001`

### Первый запуск - создание тестовых пользователей

После первого запуска создай тестовых пользователей:
```bash
curl -X POST http://localhost:8080/init-test-users
```

Это создаст 3 пользователя:
- **admin** / **admin123** — полный доступ (создание, чтение, обновление, удаление)
- **user** / **user123** — может создавать и обновлять свои элементы
- **guest** / **guest123** — только чтение (без авторизации)

### Использование веб-интерфейса

1. Открой `http://localhost:8080/` в браузере
2. Войди с одним из тестовых пользователей (например, `admin` / `admin123`)
3. Интерфейс автоматически покажет возможности в зависимости от роли:
   - **admin** — видит форму создания и все кнопки Edit/Delete
   - **user** — видит форму создания, но может редактировать только свои элементы
   - **guest** — только просмотр, без возможности создания/редактирования

## Ролевая модель доступа и IAM

Решение включает систему управления доступом с ролями и IAM-сервис:

### Роли:
- **admin** — полный доступ (создание, чтение, обновление, удаление всех элементов)
- **user** — может создавать и управлять своими элементами (чтение всех, обновление только своих)
- **guest** — только чтение (без аутентификации)

### IAM сервис (Identity and Access Management):
- `POST /auth/register` — регистрация нового пользователя (создаётся с ролью "user")
- `POST /auth/login` — аутентификация, получение JWT токена
- `POST /iam/verify` — проверка токена и получение информации о правах пользователя
- `GET /iam/user` — получение информации о текущем пользователе (требует токен)
- `POST /init-test-users` — создание тестовых пользователей (admin, user, guest)

### Быстрый старт:
1. Создай тестовых пользователей: `curl -X POST http://localhost:8080/init-test-users`
2. Открой веб-интерфейс: `http://localhost:8080/`
3. Войди с одним из пользователей:
   - **admin** / **admin123** — полный доступ
   - **user** / **user123** — создание и управление своими элементами
   - **guest** / **guest123** — только чтение

### Использование через API:
1. Зарегистрируйся: `POST /auth/register` с `{"username": "test", "password": "test123"}`
2. Войди: `POST /auth/login` с теми же данными, получи токен
3. Используй токен в заголовке: `Authorization: Bearer <token>`

## Эндпоинты CRUD (требуют аутентификации, кроме GET):
- `POST /items` — создать (требует роль user или admin, заголовок Authorization)
- `GET /items` — список (доступно всем, включая guest)
- `GET /items/<id>` — получить (доступно всем)
- `PUT/PATCH /items/<id>` — обновить (user может только свои, admin — все)
- `DELETE /items/<id>` — удалить (только admin)

Пример запроса на создание с файлом:
```bash
curl -X POST http://localhost:5000/items \
  -F "name=Test item" \
  -F "description=hello" \
  -F "file=@/path/to/local/file.png"
```
В ответе вернётся JSON с `file_url` указывающим на файл в Object Storage.

