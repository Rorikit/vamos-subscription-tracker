# Vamos Subscription Tracker

Локальное fullstack-приложение для учета участников, абонементов и занятий: выдача абонементов, списание и возврат занятий, фиксация преподавателя, учет оплат и расчет заработка преподавателей.

Интерфейс на русском языке, desktop-first. Рабочие разделы защищены входом оператора.

## Стек

- Frontend: React, TypeScript, Vite
- Стили: Tailwind CSS
- Роутинг: React Router
- API: TanStack Query
- Backend: Python, FastAPI
- База данных: SQLite
- ORM: SQLAlchemy
- Валидация: Pydantic
- Контейнеризация: Docker Compose

## Структура

```text
vamos-subscription-tracker/
├── client/
├── server/
├── launcher/
├── docker-compose.yml
└── .env.example
```

## Авторизация

Первый оператор создается автоматически при старте backend.

Значения по умолчанию для локальной разработки:

```text
Логин: operator
Пароль: vamos123
```

Для деплоя переопределите переменные окружения:

```text
AUTH_SECRET
OPERATOR_USERNAME
OPERATOR_PASSWORD
OPERATOR_FULL_NAME
AUTH_TOKEN_TTL_HOURS
```

## Запуск через Docker

```powershell
docker compose up --build
```

После запуска:

- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Остановить контейнеры:

```powershell
docker compose down
```

Остановить и удалить volume с SQLite-данными:

```powershell
docker compose down -v
```

## Локальный запуск Backend

```powershell
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend доступен на `http://127.0.0.1:8000`.

По умолчанию база создается в `server/data/app.db`. Можно переопределить:

```powershell
$env:DATABASE_URL="sqlite:///./data/app.db"
$env:AUTH_SECRET="local-secret"
$env:OPERATOR_USERNAME="operator"
$env:OPERATOR_PASSWORD="vamos123"
```

## Локальный запуск Frontend

```powershell
cd client
npm install
npm run dev -- --port 5174
```

Frontend доступен на `http://127.0.0.1:5174`.

API URL можно переопределить:

```powershell
$env:VITE_API_URL="http://localhost:8000"
```

## Сборка Windows .exe

```powershell
.\launcher\build_exe.ps1
```

Готовый файл:

```text
dist\Vamos Subscription Tracker.exe
```

`.exe` запускает backend на `http://127.0.0.1:8000`, раздает frontend на `http://127.0.0.1:5174` и хранит SQLite-базу в `%APPDATA%\Vamos Subscription Tracker\app.db`.

## Тестовые данные

Seed добавляет:

- 3 типа абонементов;
- 5 участников;
- 3 преподавателя;
- несколько активных, законченных и просроченных абонементов;
- несколько оплат;
- несколько списаний занятий с привязкой к преподавателям.

## Основные страницы

- `/login` — вход оператора.
- `/dashboard` — главная панель с активными абонементами, выручкой, занятиями и заработком преподавателей.
- `/participants` — список участников, поиск, остатки занятий и быстрые действия.
- `/participants/:id` — карточка участника с историей абонементов, посещений и оплат.
- `/memberships` — таблица всех абонементов с фильтрами по статусам.
- `/finance` — финансовая сводка и подробный заработок преподавателей за период.
- `/settings` — управление типами абонементов и преподавателями.

## Git

Репозиторий рассчитан на будущий деплой. В `.gitignore` исключены локальные базы, виртуальные окружения, `node_modules`, frontend-сборка и `.exe`-артефакты.
