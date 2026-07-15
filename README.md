# Vamos Subscription Tracker

Локальное и серверное fullstack-приложение для учета участников, абонементов, занятий, оплат и заработка преподавателей.

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
- Production reverse proxy: Caddy

## Авторизация

Первый оператор создается автоматически при старте backend.

```text
Логин: operator
Пароль: vamos123
```

Для деплоя обязательно переопределите `AUTH_SECRET`, `OPERATOR_USERNAME`, `OPERATOR_PASSWORD`, `OPERATOR_FULL_NAME`, `AUTH_TOKEN_TTL_HOURS`.

Новых пользователей можно создавать, редактировать и отключать в разделе `/settings`, блок «Пользователи».

## Финансовая модель

Финансы разделены на несколько показателей:

- «Продажи абонементов» — сумма цен абонементов по дате начала абонемента.
- «Получено оплат» — сумма неотмененных платежей по дате платежа.
- «Стоимость проведенных занятий» — клиентская стоимость только фактически проведенных и не возвращенных занятий.
- «Выплаты преподавателям» — часть стоимости проведенных занятий по проценту преподавателя.
- «Доход школы» — стоимость проведенных занятий минус выплаты преподавателям.

Формула для занятия:

```text
lesson_price = membership.price / membership.total_lessons
teacher_earning = lesson_price * teacher_share_percent / 100
school_earning = lesson_price - teacher_earning
```

Возврат занятия работает через `Visit.is_cancelled = true`: занятие остается в истории со статусом «Возвращено», возвращает одно занятие в абонемент и исключается из финансовых итогов.

## Локальный запуск через Docker

Локальный Docker-запуск использует Vite dev server на порту `5174`.

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

## Production-деплой через Docker

Для сервера добавлен отдельный production-compose:

- `docker-compose.prod.yml`
- `client/Dockerfile.prod`
- `client/nginx.conf`
- `deploy/Caddyfile`
- `.env.production.example`

Production-схема:

- `backend` запускает FastAPI на внутреннем порту `8000`;
- `frontend` собирает React-приложение и раздает статические файлы через Nginx;
- `caddy` принимает HTTP/HTTPS на портах `80` и `443`, выпускает HTTPS-сертификат и проксирует:
  - сайт на `frontend:80`;
  - API через `/api/*` на backend;
  - Swagger через `/docs`.

### Что нужно для деплоя

1. VPS с Ubuntu.
2. Домен.
3. DNS A-запись домена на IP сервера.
4. Docker и Docker Compose Plugin на сервере.
5. Открытые порты `80` и `443`.

### Команды на сервере

```bash
git clone https://github.com/Rorikit/vamos-subscription-tracker.git
cd vamos-subscription-tracker
cp .env.production.example .env
nano .env
docker compose -f docker-compose.prod.yml --env-file .env up --build -d
```

В `.env` нужно заменить минимум:

```env
DOMAIN=your-domain.com
AUTH_SECRET=long-random-secret
OPERATOR_PASSWORD=strong-password
CORS_ORIGINS=https://your-domain.com
SEED_DEMO_DATA=false
```

После запуска:

- Frontend: `https://your-domain.com`
- Backend API: `https://your-domain.com/api`
- Swagger: `https://your-domain.com/docs`

Остановить production-контейнеры:

```bash
docker compose -f docker-compose.prod.yml --env-file .env down
```

Остановить и удалить volumes, включая SQLite-базу:

```bash
docker compose -f docker-compose.prod.yml --env-file .env down -v
```

SQLite хранится в Docker volume `backend-data` внутри контейнера по пути `/app/data/app.db`.

## Автодеплой с GitHub

На сервере можно включить systemd-таймер, который раз в минуту проверяет `origin/main`.
Если в GitHub появился новый коммит, сервер подтягивает его и пересобирает production Docker Compose.

```bash
cd /opt/vamos-subscription-tracker
git pull --ff-only
sudo bash deploy/install-auto-deploy.sh
```

Проверить таймер:

```bash
systemctl status vamos-auto-deploy.timer
journalctl -u vamos-auto-deploy.service -n 100 --no-pager
```

Отключить автодеплой:

```bash
systemctl disable --now vamos-auto-deploy.timer
```

## Staging по пути /v1

Production остается доступен на корне сайта:

```text
http://168.222.140.16/
```

Staging-среда может работать на том же домене/IP по пути:

```text
http://168.222.140.16/v1/
```

Схема:

- production: ветка `main`, compose `docker-compose.prod.yml`, база `backend-data`;
- staging `/v1`: ветка `develop`, compose `docker-compose.v1.yml`, отдельная база `v1-backend-data`;
- внешний порт не открывается, `/v1` проксируется через основной Caddy.

Первичная установка staging на сервере:

```bash
cd /opt
git clone --branch develop https://github.com/Rorikit/vamos-subscription-tracker.git vamos-subscription-tracker-v1
cd vamos-subscription-tracker-v1
cp .env.v1.example .env.v1
nano .env.v1
bash deploy/install-v1-autodeploy.sh
```

В `.env.v1` обязательно заменить:

```env
AUTH_SECRET=long-random-secret
OPERATOR_PASSWORD=strong-password
```

После этого каждый push в `develop` будет обновлять staging `/v1`, а каждый push в `main` будет обновлять production.

## Backup SQLite на сервере

Production-сервер может делать ежедневный backup SQLite через systemd timer.
Backup создается online-методом SQLite, сжимается в gzip и хранится в `/opt/vamos-subscription-tracker/backups`.
По умолчанию хранятся backup-файлы за последние 14 дней.

Установить timer на сервере:

```bash
cd /opt/vamos-subscription-tracker
git pull --ff-only
sudo bash deploy/install-backup-timer.sh
```

Проверить timer и последний запуск:

```bash
systemctl status vamos-backup.timer
journalctl -u vamos-backup.service -n 100 --no-pager
ls -lh /opt/vamos-subscription-tracker/backups
```

Запустить backup вручную:

```bash
sudo systemctl start vamos-backup.service
```

Отключить backup:

```bash
sudo systemctl disable --now vamos-backup.timer
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
