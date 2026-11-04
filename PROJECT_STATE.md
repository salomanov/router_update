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
- **Router Web API:** Python 3 (`python3-light`) on port **8089** (stack_size limited to 256KB)
- **Web terminal:** `ttyd` on `127.0.0.1:7682`, public port **7681** served by an
  authenticated TCP proxy inside `router_api.py` (8KB buffer)
- **CLI:** `/opt/bin/grouter` (`plan | apply | status | update-all`)

## Router Ecosystem & Shared Ports Map (Связи сервисов на роутере)
> **ВАЖНО**: Физический роутер (192.168.1.1) делит сеть между несколькими независимыми проектами. Любые изменения портов или прокси-демонов должны учитываться смежными сервисами:
- **8089**: GRouter Web API (`router_api.py`, проект `Router_api` / `Desktop\Роутер`)
- **7681**: Терминал ttyd (`ttyd` на 7682, TCP proxy через `router_api.py`)
- **90**: Веб-панель nfqws (`lighttpd + php`)
- **1443**: `tg-ws-proxy` (WebSocket-прокси для Telegram)
- **8480**: `usque` (Cloudflare MASQUE QUIC SOCKS5, `cdnjs.cloudflare.com`, `--always-reconnect`)
- **12345**: `redsocks` (прозрачный TCP-редирект трафика ipset `WARP_YT` в SOCKS5 `8480`)
- **8085**: `nanoopds` (Книжный сервер NanoOPDS + Telegram-бот `@SalomanovBooks_Bot`, проект `E:\Projects\Opds`)
  - *Сетевая связь:* Telegram-бот ходит в `api.telegram.org` через SOCKS5 `192.168.1.1:8480` по IPv4 (`149.154.167.220:443`).
- **1883**: Mosquitto MQTT / Tuya (проект `E:\Projects\tuya_mqtt_calibrator`)

## Modular Project Architecture (RouterKit 2.0)
- `install.sh`: Мастер-инсталлятор с интерактивным меню (1: Полная, 2: Выборочная, 3-8: Быстрые режимы) и CLI-флагами (`--all`, `--dns`, `--netfilter`, `--nfqws2`, `--nfqws-web`, `--tg`, `--tailscale`, `--panel`).
- `modules/`: 7 автономных инсталляторов компонентов:
  - `01_dns.sh`: Защищенный DoT/DoH в KeeneticOS.
  - `02_netfilter_glue.sh`: NDM-хуки (перехват DNS 53, блок QUIC, сброс IPv6, MSS clamp).
  - `03_nfqws2.sh`: Движок nfqws2 Anti-DPI (без веб-панели и lighttpd).
  - `04_nfqws_web.sh`: Веб-панель nfqws (порт 90) на lighttpd+php.
  - `05_tg_proxy.sh`: Telegram WebSocket прокси (порт 1443) + команда `tg-proxy-link`.
  - `06_tailscale.sh`: Tailscale VPN + команда `tailscale-status`.
  - `07_dashboard.sh`: GRouter Панель (порт 8089) и терминал PuTTY (порт 7681).
- `netfilter/`: NDM-хуки KeeneticOS (`005-lan-fix.sh`, `010-tailscale.sh`, `015-l2tp.sh`, `020-block-quic.sh`).
- `core/`: Ядро сервисов (`api.py` со stack_size 256KB, `opkg_update.py` с автопроверкой скорости перед Range, `S90router-api`).
- `web/`: Веб-интерфейс панели (`index.html`, `app.js` с паузой опроса на `document.hidden`, `style.css`).

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

### 1. DPI bypass / media (исторически и текущее состояние)
- YouTube 4K/8K, Instagram, трекеры, Discord работают через nfqws2 + списки доменов.
- Стандартная стратегия nfqws2 (`circular:fails=2:time=300:retrans=3:nld=2` с multisplit и `fastpath-workaround=auto`). Списки очищены от накопившихся ложных срабатываний в `auto.list`.
- `020-block-quic.sh`, `015-l2tp.sh`, `005-lan-fix.sh`: блокировка QUIC (UDP 443) по IPv4/IPv6, немедленный сброс IPv6-форвардинга (исключение Happy Eyeballs таймаутов при отсутствии IPv6 WAN), принудительный редирект DNS (порт 53) в локальный DoH/SmartDNS и TCP MSS Clamping to PMTU (1360 для L2TP).
- Bambu Lab S3, Entware, Kaspersky и служебные домены — в `exclude.list`.
- `user.list` — стандартный чистый список доменов (273 записи).
- **DNS Upstreams & AI Resolution**: апстрим `xbox-dns.ru` (порт 40508) отвечает за 6 мс и перехватывает запросы к `chatgpt.com` и `gemini.google.com`, возвращая `0.0.0.0` (ERR_NAME_NOT_RESOLVED / ERR_CONNECTION_CLOSED). Для работы ChatGPT/Gemini в РФ необходимы специализированные SmartDNS (`dns.dns-ai.ru`, `dns.malw.link`, `geohide.ru`), а `xbox-dns.ru` должен использоваться изолированно для консолей или удалён из общих апстримов.

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

### 6. Проверено на живом роутере (2026-10-29, 192.168.1.1, MIPS, KeeneticOS)
Обновление поверх старой сборки `fe6404c` (в ней был бэкдор `admin/Salomanov|keenetic`
и ttyd на `0.0.0.0:7681` с паролем, напечатанным на экране).
- Вход `admin` / `Salomanov` — 200, `must_change_password=false`, принудительной смены нет.
- `admin` / `keenetic` и неверный пароль — 401 (fallback удалён из кода).
- `/api/plan` — 200, профиль `home-router` сходится: `missing: []`, `outdated: []`.
- `7681`: без cookie — 401, с чужой cookie — 401, с сессией — 200, WebSocket `/ws` — 101.
- `7682` снаружи недоступен (только `127.0.0.1`).
- Логаут — 200 мгновенно, токен отозван, повторный вход сразу после логаута работает
  (дедлок не воспроизводится).
- `grouter plan` на роутере — exit 0; `grouter status` показывает службы.
- Резервная копия прежней сборки: `/opt/etc/grouter/backup_20261029_125858/`.

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
11. В init-скрипте `S90router-api` только целочисленный `sleep`: BusyBox на KeeneticOS
    отвечает `sleep: invalid number '0.5'`, и ожидание порта превращается в холостой цикл.
12. Проверка терминала из PowerShell через ручной заголовок `Cookie` даёт ложный `401`:
    PS 5.1 его не отправляет. Тестировать прокси только через Python/socket или `-WebSession`.

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

## Standalone USB Flasher («Вставил и работает»)
- `RouterKitFlasher.exe` (20.8 МБ): Автономное Windows-приложение (не требует установленного Python на ПК).
  - Запуск двойным кликом на Windows (встроен манифест UAC для прав Администратора).
  - Автоматическое обнаружение подключенных USB-накопителей с безопасной фильтрацией системных дисков (`C:`, SATA/NVMe).
  - Запрос подтверждения перед записью: *"Точно ли шьём? Все данные будут удалены [Y/N]"*.
  - Автоматическое размонтирование и блокировка разделов Windows (`FSCTL_LOCK_VOLUME`, `FSCTL_DISMOUNT_VOLUME`, `Clear-Disk`).
  - Поблочная прямая запись загрузочного образа (`\\.\PhysicalDriveN`) с динамическим прогресс-баром и расчётом скорости.
- `routerkit-mipsel.img.gz` (12.6 МБ): Сжатый мастер-образ (MBR + ext4 раздел 256 МБ с меткой `ENTWARE`):
  - Базовое окружение Entware (BusyBox, Opkg, Dropbear SSH, библиотеки).
  - Офлайн-пакеты: `python3-base`, `libpython3`, `python3`, `ipset`, `iptables`, `nfqws2-keenetic`.
  - Модуль обхода блокировок: бинарник `nfqws2` (MIPS), конфигурация с круговым мультисплитом (`nfqws2.conf`), проверенные списки доменов.
  - Сетевые NDM-хуки: `005-lan-fix.sh`, `015-l2tp.sh`, `020-block-quic.sh`, `100-nfqws2.sh`.
  - Панель управления GRouter: веб-интерфейс (`index.html`, `app.js`, `style.css`) и бэкенд `router_api.py` на порту 8089.
  - Скрипт первого запуска `/opt/etc/init.d/S01auto-setup`: автоматически настраивает DoT DNS в KeeneticOS через `ndmc`, сохраняет конфиг в flash роутера и запускает службы.
  - Результат для пользователя: флешка извлекается из ПК, вставляется в любой роутер Xiaomi Mi 3G (KeeneticOS) и через 15-20 секунд всё работает автоматически без консоли.

## Current State & Recent Changes
- [x] Внедрен асинхронный TaskRunner и стриминг логов в реальном времени (`/api/task/active`, модальная живая консоль в UI с таймером и автоскроллом для `update_all`, `apply` и установки пакетов).
- [x] Добавлен мониторинг сервисов экосистемы (`NanoOPDS` :8085, `Mosquitto` :1883, `Tuya Calibrator`, `Usque` :8480) с портами, бейджами и прямыми кнопками открытия Web UI.
- [x] Реализована мобильная адаптация терминала PuTTY: режим «На весь экран», масштабирование 100vh, экранные клавиши (`Ctrl+C`, `Tab`, `Esc`, `▲`, `▼`, `Enter`, быстрые сниппеты).
- [x] Создан автономный EXE-прошивальщик `RouterKitFlasher.exe` (`--onefile`, `--uac-admin`, встроенный `routerkit-mipsel.img.gz`).
- [x] Создан несгораемый релизный архив `.backups/desktop_release_2026-11-01_16-45-21/` с SHA256-хэшами и Git-тегом `desktop-v2026-11-01_16-45-21`.
- [x] Устранён спам бэктрейсов Tailscale IPv6 (`sysctl -w net.ipv6.conf.tailscale0.disable_ipv6=1` в `/opt/etc/init.d/S06tailscale`).
- [x] Удален неработающий DoH/DoT апстрим `dns.malw.link` из `dns-proxy` в KeeneticOS (`no https upstream`, `no tls upstream`).
- [x] Исправлен доступ к `4pda.to`, `bambulab.com` и `makerworld.com`: домены убраны из `user.list`/`auto.list` и добавлены в `exclude.list`, предотвращая сброс соединений Cloudflare (`ERR_CONNECTION_RESET`).
- [x] Все изменения зафиксированы и запушены в ветку `main` репозитория `https://github.com/salomanov/router_update.git`.
- [x] Строго соблюдено правило локальной работы: 0 подключений к удаленному роутеру.

## Next Steps
- Прогнать `install.sh` на **чистом** роутере (не обновление): проверить установку пакетов,
  баннер с паролем, `grouter apply`.
- Проверить установку из каталога на живом устройстве (пакеты и скрипты).
- Убедиться, что порты 8089 и 7681 не проброшены в интернет (в панели Keenetic — «Переадресация портов»).
- Убедиться, что nfqws-web (порт 90) отдаёт 401 без креды после обновления пакета.
