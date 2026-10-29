# PROJECT_STATE.md

## Project Information
- **Project Name:** Router Update & Bypass System (Xiaomi Mi WiFi Router 3G v1)
- **Repository:** `https://github.com/salomanov/router_update.git`

## Product Goals (не менять без владельца)
1. Развернуть «свой набор» пакетов на новом роутере **одной командой**.
2. Легко **проверять и обновлять** установленное (список, версии, «есть обновление», обновить всё).
3. **Выполнять команды на роутере из браузера** так же, как в PuTTY.

Всё остальное (красивые карточки, GitHub-релизы, второстепенные сервисы) — вторично.
Новые функции добавляются только если приближают эти три сценария.

## Non-goals
- Мультитенантность, роли, несколько пользователей панели.
- Публичный доступ к root-shell без аутентификации.
- Хранение любых паролей/токенов в репозитории.

## Architecture & Environment
- **Device:** Xiaomi Router 3G v1 (R3Gv1), MIPS, 128 MB RAM
- **Firmware:** KeeneticOS (KN-2410 / KN-1810 mod), Entware on `/opt`
- **Shell:** BusyBox ash (нет `pipefail`, нет bash-массивов)
- **DPI Bypass Engine:** `nfqws2-keenetic` (LUA zapret engine)
- **Router Web API:** Python 3 (`python3-light`) on port **8089**
- **Web terminal:** `ttyd` on `127.0.0.1:7682`, public port **7681** served by an
  authenticated TCP proxy inside `router_api.py`
- **CLI:** `/opt/bin/grouter` (`plan | apply | status | update-all`)

## Security Model (October 2026)
- **Пароль по умолчанию — `Salomanov`** (требование владельца: домашняя панель, не выставляется
  в интернет). `init_auth()` хэширует его в `/opt/etc/router-api.auth` при первом старте,
  принудительной смены нет. Смена пароля доступна всегда: кнопка с ключом в шапке панели
  или `POST /api/password`.
- Переопределяется при установке: `GROUTER_DEFAULT_PASSWORD=<свой>` (пишется в
  `/opt/etc/grouter/default_password`, удаляется после хэширования) или
  `GROUTER_RANDOM_PASSWORD=1` — одноразовый случайный пароль + обязательная смена.
- `verify_credentials()` проверяет **только** PBKDF2-хэш из `/opt/etc/router-api.auth`.
  Любой «аварийный fallback» запрещён — это бэкдор.
- Сессии: `grouter_session` (HttpOnly, SameSite=Lax, 7 дней) + `Authorization: Bearer`
  для POST. Query-string токены (`?token=`) не принимаются.
- Блокировка после 5 неудачных попыток входа с одного IP на 5 минут (HTTP 429).
- `POST /api/password` — смена пароля (старый + новый, минимум 10 символов), после смены
  все сессии отзываются.
- В режиме `GROUTER_RANDOM_PASSWORD=1` (`must_change_password = true`) разрешены только
  `/api/status`, `/api/plan`, `/api/auth/check`, `/api/password` и `/api/logout`; остальное — `403`.
- CORS: заголовок отдаётся только для собственного origin (совпадение с `Host`), wildcard убран.
- Установщики каталога скачиваются в файл, проверяются на непустоту и только потом
  запускаются. Пайп `curl ...` в `sh` запрещён (статус пайплайна принадлежит `sh`).
- Клиентский `install_cmd` игнорируется: команда берётся только из серверного каталога.

## Осознанные исключения по безопасности
- Стандартный пароль `Salomanov` в коде/README/UI — по прямому требованию владельца.
  Условия: панель в домашней LAN, порт 8089 не проброшен в интернет, смена пароля работает.
  Занесено в `.security-gate-allow` (строка с `Salomanov`), чтобы гейт не «зеленел» молча.
- `subprocess.run(..., shell=True)` в `/api/exec` — это и есть root-shell панели.
  Условия: только с Bearer-токеном, команда ≤ 512 символов, одна за раз, с аудитом.

## Current Working State

### 1. DPI bypass / media (исторически)
- YouTube 4K/8K, Instagram, трекеры, Discord работают через nfqws2 + списки доменов.
- `020-block-quic.sh` блокирует QUIC (UDP 443) по IPv4 и IPv6, форсируя TCP + desync.
- Bambu Lab S3 и служебные домены — в `exclude.list`.
- `user.list` — 412+ доменов, пополняется по мере необходимости.

### 2. OPKG updates
- `opkg_update.py`: скачивание `Packages.gz` чанками по 30 КБ через HTTP Range
  (обход DPI-обрыва на ~33 КБ), проверка `206 Partial Content`, 3 попытки на чанк,
  gzip-проверка, атомарная замена.
- Репозитории читаются из `/opt/etc/opkg.conf` и `/opt/etc/opkg/*.conf`, а не из
  захардкоженного списка.
- Устаревший `/opt/tmp/opkg.lock` удаляется только если процесс `opkg` не запущен
  (никаких `killall -9`).

### 3. Web panel
- Динамическое обнаружение служб в `/opt/etc/init.d/S*`, кэш discovery/статусов 3 с.
- Вкладки: «Установленные службы», «Каталог приложений», «Терминал PuTTY».
- Кнопки профиля: «Проверить профиль» (`/api/plan`), «Применить профиль» (`/api/apply`),
  «Обновить всё» (`/api/update_all`).
- Флаг `update_available` считается на бэкенде (`is_newer_version`), фронтенд не сравнивает
  версии строками.
- Логи: `RotatingFileHandler` (512 КБ × 3).

### 4. Web terminal
- `S96ttyd`: `ttyd -W -i 127.0.0.1 -p 7682 /opt/bin/sh` — только loopback.
- Прокси в `router_api.py` слушает `7681`, проверяет cookie сессии панели; без входа — `401`.
- Пароль терминала отдельно не нужен: авторизация = сессия панели.

### 5. nfqws web UI (порт 90)
- Аутентификация **не отключается**: это UI управления firewall/desync.
- Учётные данные не инжектятся в чужой PHP; при необходимости задаются штатным
  `/opt/etc/nfqws_web.conf`.

## Известные исправления (не сломать повторно)
1. `get_service_status`: негативные статусы (`not running`, `stopped`, `dead`, `inactive`)
   проверяются **до** позитивных; финальная истина — `pidof`.
2. `/api/logout` не вызывает `save_sessions()` под `_SESSIONS_LOCK` (был вечный дедлок).
3. Обновление `tg-ws-proxy` сохраняет и восстанавливает `secret.conf` / `config.conf` (0600).
4. `discover_services()` всегда возвращает dict с полем `script`; `os.path.*` не получает `None`.
5. Кастомные init-скрипты удаляются перемещением в `/opt/etc/init.d.disabled/`, а не `os.remove`.
6. Учётные данные отсутствуют в коде, документации, логах и баннерах установки.
7. Ни один сетевой сервис (7681, 90, 8089) не отвечает без аутентификации.
8. Все загрузки в установщиках — в файл, с проверкой непустоты и кода возврата; без пайпа в `sh`.
9. `usque` использует единый путь, определённый по init-скрипту (`resolve_usque_path()`).
10. `install_cmd` из тела запроса не выполняется; `shell=True` остался только в `/api/exec`
    (это его назначение), команда ограничена 512 символами, выполняется по одной, с аудитом.

## Key Configuration Files
- `/opt/etc/grouter/profile.json`: профиль пакетов/служб/репозиториев.
- `/opt/etc/router-api.auth`: PBKDF2-хэш пароля администратора (0600).
- `/opt/etc/router-api.sessions`: активные сессии (0600).
- `/opt/etc/grouter/initial_password`: одноразовый пароль, удаляется после смены (только secure-режим).
- `/opt/etc/nfqws2/nfqws2.conf`, `configs/nfqws2.conf`: Anti-DPI конфигурация.
- `/opt/etc/nfqws2/lists/user.list`: домены для desync (413+).
- `/opt/etc/nfqws2/lists/exclude.list`: исключения (Bambu Lab S3, Entware).
- `/opt/etc/ndm/netfilter.d/020-block-quic.sh`: блокировка QUIC IPv4/IPv6.
- `/opt/scripts/router_api.py`: API панели + прокси ttyd.
- `/opt/scripts/opkg_update.py`: устойчивое обновление списков OPKG.
- `/opt/scripts/grouter_cli.py`, `/opt/bin/grouter`: CLI профиля.
- `/opt/share/router-control-center/`: фронтенд (`index.html`, `app.js`, `style.css`).

## Next Steps
- Прогнать `install.sh` на чистом роутере и проверить: генерацию пароля, смену пароля,
  вход в терминал только после логина, `grouter plan/apply`.
- Проверить установку из каталога на живом устройстве (пакеты и скрипты).
- Убедиться, что nfqws-web (порт 90) отдаёт 401 без креды после обновления пакета.
