# Vamos Subscription Tracker

Локальное fullstack-приложение для учета участников, абонементов, занятий, оплат и заработка преподавателей.

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

## Авторизация

Первый оператор создается автоматически при старте backend.

```text
Логин: operator
Пароль: vamos123
```

Для деплоя переопределите `AUTH_SECRET`, `OPERATOR_USERNAME`, `OPERATOR_PASSWORD`, `OPERATOR_FULL_NAME`, `AUTH_TOKEN_TTL_HOURS`.

Новых пользователей можно создавать, редактировать и отключать в разделе `/settings`, блок «Пользователи».

## Финансовая модель

Финансы разделены на несколько разных показателей:

- «Продажи абонементов» — сумма цен абонементов по дате начала абонемента.
- «Получено оплат» — сумма неотмененных платежей по дате платежа.
- «Стоимость проведенных занятий» — клиентская стоимость только фактически проведенных и не возвращенных занятий.
- «Выплаты преподавателям» — часть стоимости проведенных занятий по проценту преподавателя.
- «Доход школы» — стоимость проведенных занятий минус выплаты преподавателям.

Продажи абонементов не равны доходу школы: деньги за еще не проведенные занятия не считаются заработком школы.

Формула для занятия:

```text
lesson_price = membership.price / membership.total_lessons
teacher_earning = lesson_price * teacher_share_percent / 100
school_earning = lesson_price - teacher_earning
```

Процент преподавателя настраивается в карточке преподавателя в разделе `/settings`.

При списании занятия финансовые значения сохраняются в `Visit`: `lesson_price`, `teacher_share_percent`, `teacher_earning`, `school_earning`. Поэтому изменение цены абонемента или процента преподавателя не пересчитывает старые занятия.

Возврат занятия работает через `Visit.is_cancelled = true`: занятие остается в истории со статусом «Возвращено», возвращает одно занятие в абонемент и исключается из финансовых итогов.

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

## Локальный запуск Frontend

```powershell
cd client
npm install
npm run dev -- --port 5174
```

Frontend доступен на `http://127.0.0.1:5174`.

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
- 3 преподавателя с процентом преподавателя;
- несколько абонементов;
- несколько оплат;
- несколько списаний занятий с финансовым снимком.

## Основные страницы

- `/login` — вход оператора.
- `/dashboard` — главная панель.
- `/participants` — список участников, поиск и быстрые действия.
- `/participants/:id` — карточка участника с историей абонементов, посещений и оплат.
- `/memberships` — таблица абонементов.
- `/finance` — продажи, оплаты, стоимость проведенных занятий, выплаты преподавателям и доход школы.
- `/settings` — пользователи, типы абонементов и преподаватели.

## Тесты

Backend-тесты:

```powershell
cd server
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Frontend-сборка:

```powershell
cd client
npm run build
```

## Git

В `.gitignore` исключены локальные базы, виртуальные окружения, `node_modules`, frontend-сборка и `.exe`-артефакты.
