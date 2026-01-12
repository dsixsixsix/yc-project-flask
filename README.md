# Минимальный CRUD c Flask + SQLite + S3-совместимым Object Storage

## Что есть
- Framework: Flask.
- БД: SQLite (можно заменить через `DATABASE_URL`).
- Object Storage: S3-совместимый (MinIO/AWS). Файлы загружаются и URL сохраняется в таблицу.
- CRUD для сущности `Item`: `id`, `name`, `description`, `file_url`.

## Подготовка
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

## Эндпоинты
- `POST /items` — создать. Параметры: `name` (form-data), опционально `description`, файл `file` (multipart).
- `GET /items` — список.
- `GET /items/<id>` — получить.
- `PUT/PATCH /items/<id>` — обновить поля `name`, `description`, заменить файл.
- `DELETE /items/<id>` — удалить.

Пример запроса на создание с файлом:
```bash
curl -X POST http://localhost:5000/items \
  -F "name=Test item" \
  -F "description=hello" \
  -F "file=@/path/to/local/file.png"
```
В ответе вернётся JSON с `file_url` указывающим на файл в Object Storage.

