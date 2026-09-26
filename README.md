# GRouter Ecosystem — Полная экосистема для роутера Keenetic / Entware

Готовый программный комплекс для роутеров с **KeeneticOS** и средой **Entware** (Xiaomi Mi Router 3G, Keenetic Extra, Giga, Viva, 4G III и др.).

### Что входит в экосистему:
1. 🎛️ **GRouter Control Panel** — современная веб-панель мониторинга ресурсов (CPU, RAM, диск), статуса и перезапуска служб, логов и автообновлений.
2. ⚡ **nfqws2 (Anti-DPI)** — проверенный обход блокировок РКН/ТСПУ: YouTube 4K/Shorts без буферизации, Instagram (лента, сторис, рилсы), торрент-трекеры (Rutracker, NNM-Club и фотохостинги), Discord (голос/медиа), облако Bambu Lab 3D.
3. 🛡️ **Tailscale Exit Node** — защищенный удаленный VPN-доступ к домашней сети и незаблокированному интернету из любой точки мира (с мобильного телефона или ноутбука) с фаерволом против зависаний и перехватов.
4. ✈️ **Telegram WebSocket Proxy (tg-ws-proxy)** — собственный быстрый MTProto-прокси для Telegram прямо на роутере.

---

## Подготовка нового роутера (Займет 2 минуты)

Перед установкой скриптов на чистом роутере нужно сделать 3 простых шага:

1. **Подключите USB-накопитель:** вставьте в роутер любую USB-флешку (рекомендуется отформатировать в `ext4` или `NTFS`).
2. **Включите Entware (OPKG) в веб-интерфейсе Keenetic:**
   * Откройте в браузере `http://192.168.1.1` (войдите под своим логином/паролем администратора).
   * Перейдите в раздел **«Управление»** → **«Приложения»** (или *«OPKG»*).
   * В пункте **«Хранилище пакетов OPKG»** выберите подключенную флешку и нажмите **«Сохранить»**.
   * Дождитесь появления надписи *«Установлена система OPKG (Entware)»*.
3. **Подключитесь к роутеру по SSH:**
   * Откройте терминал (PowerShell или командную строку на компьютере) и выполните:
     ```sh
     ssh -p 222 root@192.168.1.1
     ```
     *(Стандартный пароль в Entware: `keenetic`)*.

---

## Вариант 1: Установка ВСЕГО одной командой (All-in-One) 🚀

Если вы хотите сразу получить настроенный роутер «под ключ» со всеми сервисами:

```sh
curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_all.sh | sh
```

### Что сделает скрипт автоматически:
1. Установит и запустит **веб-панель управления** (`http://192.168.1.1:8089/`).
2. Подключит репозиторий и установит **nfqws2** с готовыми оптимизированными профилями desync, базой из 360+ хостов (`user.list`), правилами для YouTube, Instagram, трекеров и исключениями для Bambu Lab.
3. Установит и запустит собственный **Telegram Proxy** (`tg-ws-proxy` на порту 1443).
4. Установит **Tailscale**, настроит драйвер TUN, автозапуск, NAT и фаервол с защитой от QUIC-зависаний и MTU-дропов. В конце скрипт выведет ссылку для привязки роутера к вашему аккаунту Tailscale.

---

## Вариант 2: Покомпонентная установка

Если вам нужны только определенные сервисы, вы можете запускать их раздельно:

### 1. Только веб-панель управления (GRouter Control Panel)
```sh
curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install.sh | sh
```
* После установки панель доступна в локальной сети: **`http://192.168.1.1:8089/`**.
* Дополнительно веб-панель можно захостить на GitHub Pages (см. раздел ниже).

### 2. Только обход блокировок (nfqws2)
```sh
curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_nfqws2.sh | sh
```
* Загружает проверенные desync-стратегии: `fake:blob=stun`, `fake:blob=tls_google`, `fakedsplit`.
* Включает списки хостов для YouTube, Meta/Instagram, NNM-Club, FastPic, Rutracker, Discord.
* Перезапуск службы: `/opt/etc/init.d/S51nfqws2 restart`.

### 3. Только Tailscale (VPN Exit Node + удаленный доступ)
```sh
curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_tailscale.sh | sh
```
* Включает IP forwarding и TUN интерфейс.
* Настраивает правила iptables:
  * Моментальный сброс QUIC (`REJECT UDP 443`) для исключения тайм-аутов в Instagram/YouTube на телефонах.
  * Фиксация `TCPMSS 1240` под MTU 1280 туннеля (0 потерь пакетов при передаче тяжелых медиа).
  * Перехват DNS на порту 53 в защищенный DoH роутера.
* Выводит ссылку `https://login.tailscale.com/a/...` для авторизации в вашем Tailscale аккаунте.

### 4. Только Telegram WebSocket Proxy
```sh
curl -sL https://raw.githubusercontent.com/salomanov/router_update/main/install_tg_proxy.sh | sh
```
* Запускает прокси на порту 1443.
* Ссылка для подключения генерируется автоматически и видна в веб-панели управления.

---

## Настройка удаленного доступа с телефона (Tailscale)

После запуска `install_tailscale.sh` выполните 3 простых шага в веб-интерфейсе Tailscale:

1. **Активация Exit Node:**
   * Откройте консоль [Tailscale Machines](https://login.tailscale.com/admin/machines).
   * Найдите ваш роутер (например, `xiaomi-r3gv1`), нажмите `...` справа от него → **Edit route settings...**.
   * Поставьте галочки напротив:
     * `Use as exit node` (`0.0.0.0/0` и `::/0`)
     * Подсеть домашней сети: `192.168.1.0/24`
   * Нажмите **Save**.
2. **Включение на телефоне:**
   * Установите приложение **Tailscale** на телефон (из Google Play или App Store) и войдите в тот же аккаунт.
   * Нажмите на значок щита (Exit Node) и выберите ваш роутер.
   * Теперь весь трафик телефона шифруется и идет через домашний роутер со всеми обходами блокировок.
3. **Важная защита от подмены DNS операторами (на Android):**
   * В настройках телефона: **«Подключение и общий доступ»** → **«Частный DNS-сервер» (Private DNS)**.
   * Впишите имя хоста: `dns.google` или `one.one.one.one` и сохраните.
   *(Это защитит телефон от подделки DNS-ответов сторонними Wi-Fi провайдерами в кафе, отелях и на работе).*

---

## Настройка облачного доступа к панели через KeenDNS (HTTPS)

Если у вас настроен KeenDNS (например, `salomanov.crazedns.ru`), вы можете открыть веб-панель управления роутером из любой точки интернета по безопасному SSL-соединению:

1. Подключитесь по SSH к роутеру с KeenDNS (порт 22 или 222).
2. Выполните команды настройки проксирования:
   ```sh
   ip http proxy panel upstream http 192.168.1.1 8089
   ip http proxy panel allow public
   system configuration save
   ```
3. Теперь ваша панель доступна по всему миру:
   👉 **`https://panel.salomanov.crazedns.ru`**

---

## Структура репозитория

```
├── install_all.sh            # All-in-one автоустановщик (все сервисы одной командой)
├── install.sh                # Установщик веб-панели управления GRouter
├── install_nfqws2.sh         # Установщик nfqws2 Anti-DPI со всеми списками и блобами
├── install_tailscale.sh      # Установщик Tailscale VPN Exit Node с защитой фаервола
├── install_tg_proxy.sh       # Установщик Telegram WebSocket Proxy
├── router_api.py             # Бэкенд API-сервера панели на Python 3
├── S90router-api             # Init-скрипт автозапуска API-сервера
├── index.html, style.css, app.js # Статический фронтенд веб-панели
└── configs/                  # Резервная копия эталонных конфигураций
    ├── nfqws2.conf           # Конфигурация desync-профилей nfqws2
    ├── lists/                # user.list (360+ доменов), exclude.list, ipset
    ├── blobs/                # Бинарные дампы TLS ClientHello, STUN, Discord UDP
    ├── opkg/                 # Репозитории feedly и nfqws2-keenetic
    └── ndm/010-tailscale.sh  # Эталонные правила фаервола
```

---

## Полезные команды на роутере

| Действие | Команда |
| :--- | :--- |
| Статус всех сервисов | `http://192.168.1.1:8089/api/status` |
| Перезапуск панели API | `/opt/etc/init.d/S90router-api restart` |
| Перезапуск nfqws2 | `/opt/etc/init.d/S51nfqws2 restart` |
| Просмотр лога nfqws2 | `tail -f /opt/var/log/nfqws2.log` |
| Статус Tailscale | `/opt/bin/tailscale status` |
| Ссылка на прокси Telegram | `/opt/etc/init.d/S99tg-ws-proxy status` |
| Свободная память и диск | `free -m; df -h /opt` |
