# Отчет по обновлению роутера - 2026-05-30

Этот файл нужен, чтобы можно было продолжить работу, если история диалога потеряется.

## Доступ к роутеру

- Роутер: `192.168.1.1`
- SSH: порт `222`
- Логин: `root`
- Пароль в файл намеренно не сохранен.
- Устройство/ядро, зафиксировано ранее:

  ```text
  Linux Xiaomi_R3Gv1 4.9-ndm-5 #0 SMP Thu Apr 30 13:20:11 2026 mips GNU/Linux
  ```

- Entware смонтирован в `/opt` с `/dev/sda1`.

## Что было проверено

1. SSH-доступ работает через Python/Paramiko.
2. `opkg` найден по пути `/opt/bin/opkg`.
3. Версия менеджера пакетов Entware:

   ```text
   opkg version 38eccbb1fd694d4798ac1baf88f9ba83d1eac616 (2024-10-16)
   ```

4. Свободное место:

   ```text
   /dev/sda1 on /opt type ext4
   14.2G total, 13.4G free
   ```

5. Основные фиды Entware:

   ```text
   src/gz entware http://bin.entware.net/mipselsf-k3.4
   src/gz keendev http://bin.entware.net/mipselsf-k3.4/keenetic
   ```

6. Дополнительные фиды `opkg`:

   ```text
   /opt/etc/opkg/feedly.conf:
   src/gz feedly_mipsel-3.4 https://spatiumstas.github.io/feedly/mipsel-3.4

   /opt/etc/opkg/nfqws-keenetic-web.conf:
   src/gz nfqws-keenetic-web https://nfqws.github.io/nfqws-keenetic-web/all

   /opt/etc/opkg/nfqws2-keenetic.conf:
   src/gz nfqws2-keenetic https://nfqws.github.io/nfqws2-keenetic/all
   ```

## Что было запущено на роутере

Время и uptime во время проверки:

```text
Sat May 30 13:52:53 MSK 2026
up 2 days, 15:29
load average: 0.10, 0.13, 0.15
```

Пользовательские/Entware-сервисы:

```text
dropbear              SSH на порту 222
nfqws2                anti-DPI/zapret, qnum 300
tg-ws-proxy           Telegram WS proxy, порт 1443
mosquitto             MQTT broker, порт 1883
lighttpd              веб-сервер, порты 8088 и 90
tuya_mqtt_calibrator  /opt/scripts/tuya_mqtt_calibrator.py, 2 процесса
```

Скрипты автозапуска в `/opt/etc/init.d`:

```text
S51dropbear
S51nfqws2
S61tg-ws-proxy
S80lighttpd
S80mosquitto
S99tuya-mqtt-calibrator
S99usque
```

Статус сервисов до обновления:

```text
S61tg-ws-proxy: alive
S99usque: Usque SOCKS5 is stopped
```

Сетевые слушатели, на которые стоит обращать внимание:

```text
0.0.0.0:222   /opt/sbin/dropbear
0.0.0.0:1443  tg-ws-proxy
0.0.0.0:1883  mosquitto
0.0.0.0:8088  lighttpd
0.0.0.0:90    lighttpd
0.0.0.0:23    telnetd
```

Секреты были скрыты в выводе чата и в этом файле.

## tg-ws-proxy до обновления

Установленный пакет до обновления:

```text
Package: tg-ws-proxy
Version: 0.5-1
Architecture: mipsel-3.4
Config: /opt/etc/tg-ws-proxy.conf
Binary: /opt/bin/tg-ws-proxy
```

Конфиг до обновления, секрет скрыт:

```text
HOST=0.0.0.0
PORT=1443
SECRET=<redacted>
LOG_LEVEL=0
DC_IP_DEFAULT=149.154.167.220
DC_IP_DEFAULT_POOL=""
EXTRA_ARGS=""
```

Результат `opkg update`:

- Основные фиды Entware обновились успешно:
  - `http://bin.entware.net/mipselsf-k3.4`
  - `http://bin.entware.net/mipselsf-k3.4/keenetic`
- Три HTTPS-фида не скачались, потому что роутерный `wget` сообщил `not an http or ftp url` для HTTPS:
  - `https://spatiumstas.github.io/feedly/mipsel-3.4`
  - `https://nfqws.github.io/nfqws-keenetic-web/all`
  - `https://nfqws.github.io/nfqws2-keenetic/all`

Доступное обновление `tg-ws-proxy` через `opkg`:

```text
tg-ws-proxy - 0.5-1 - 0.7.2-1
```

`opkg info tg-ws-proxy` показывал:

```text
Package: tg-ws-proxy
Version: 0.7.2-1
Depends: ca-certificates
Section: net
Architecture: mipsel-3.4
Size: 1691737
Filename: tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
Description: Telegram MTProto WS bridge proxy (Go binary)
```

Проверенные источники:

- Entware-совместимый релиз:
  - `https://github.com/spatiumstas/tg-ws-proxy-go/releases/tag/0.7.2`
  - Asset: `tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk`
  - Asset URL: `https://github.com/spatiumstas/tg-ws-proxy-go/releases/download/0.7.2/tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk`
- Официальный upstream Flowseal:
  - `https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.7.0`
  - Published: `2026-05-16T08:36:48Z`
  - В релизе Flowseal есть сборки `linux_amd64`, macOS и Windows, но нет MIPS/MIPSel-сборки. Для этого MIPS-роутера практичный путь обновления - Entware-пакет `0.7.2-1`.

## Usque до обновления

Файлы на роутере:

```text
/opt/etc/init.d/S99usque
/opt/tmp/install_usque_fixed.sh
/opt/usr/bin/usque
/opt/usr/bin/config.json
/opt/var/run/usque.pid
```

Состояние сервиса до обновления:

```text
Usque SOCKS5 is stopped.
```

Версия до обновления:

```text
usque version: v2.0.1
Commit: 24af7b21a56b083b86405597654b517b92f437af
Build Date: 2026-04-10T18:49:50Z
```

Бинарник до обновления:

```text
/opt/usr/bin/usque
size: 13238487 bytes
md5: 60742a003f252a29e2de25a7936b7303
```

Команда запуска из `/opt/etc/init.d/S99usque`:

```sh
PROG=/opt/usr/bin/usque
CONFIG_FILE=/opt/usr/bin/config.json
ARGS="socks -S -b 192.168.1.1 -p 8480 -d 1.1.1.1 -d 1.0.0.1 -s ozon.ru"
DESC="Usque SOCKS5"
PIDFILE=/opt/var/run/usque.pid
BIND_IP="192.168.1.1"
TARGET_DOMAIN="ozon.ru"
```

Проверенный upstream-релиз:

- Repository: `https://github.com/Diniboy1123/usque`
- Latest release: `v3.0.0`
- Release URL: `https://github.com/Diniboy1123/usque/releases/tag/v3.0.0`
- Published: `2026-04-22T00:01:29Z`
- Есть MIPS little-endian asset:
  - `usque_3.0.0_linux_mipsle.zip`
  - Asset URL: `https://github.com/Diniboy1123/usque/releases/download/v3.0.0/usque_3.0.0_linux_mipsle.zip`
  - Size: `4493822`
- Checksums:
  - `https://github.com/Diniboy1123/usque/releases/download/v3.0.0/checksums.txt`

Вывод по Usque перед обновлением:

- Доступно обновление `v2.0.1` -> `v3.0.0`.
- На этом роутере Usque не управляется через `opkg`; обновление делается ручной заменой бинарника.
- Сервис был остановлен, поэтому риск обновления ниже, но файл `/opt/usr/bin/config.json` нужно сохранять.

## Обновление выполнено - 2026-05-30

Перед обновлением создан бэкап на роутере:

```text
/opt/tmp/codex-update-backup-20260530-135709
```

В бэкап вошли:

```text
/opt/etc/tg-ws-proxy.conf
/opt/etc/init.d/S61tg-ws-proxy
/opt/bin/tg-ws-proxy
/opt/etc/init.d/S99usque
/opt/usr/bin/usque
/opt/usr/bin/config.json
```

Локальные загрузки сохранены в рабочей папке:

```text
downloads/tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
downloads/usque_3.0.0_linux_mipsle.zip
downloads/usque_checksums.txt
```

Локально зафиксированные хэши:

```text
tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
SHA256: 7A629E962EC259904AE1AB0E71D762551523B47BB7D32856C951DB306496AF82

usque_3.0.0_linux_mipsle.zip
SHA256: C519A9F7BF258EBB1B83499D1773EFC0F76332D0081CAB74989B042B8176BF86
```

SHA256 для Usque совпал с upstream-файлом `checksums.txt`.

### Результат обновления tg-ws-proxy

Прямая команда `opkg upgrade tg-ws-proxy` не сработала, потому что `opkg` пытался скачать пакет из HTTPS-фида через сборку `wget` без поддержки HTTPS:

```text
wget: not an http or ftp url: https://spatiumstas.github.io/feedly/mipsel-3.4/tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
```

Использованный обход:

1. `.ipk` скачан локально на Windows.
2. Файл загружен на роутер через SSH-канал `cat > file`, потому что SFTP в Dropbear на роутере недоступен.
3. Пакет установлен локально:

   ```sh
   opkg install /opt/tmp/tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
   ```

Пакет успешно обновлен:

```text
Package: tg-ws-proxy
Version: 0.7.2-1
Status: install user installed
Architecture: mipsel-3.4
```

Важная деталь миграции:

- Старый пакет использовал `/opt/etc/tg-ws-proxy.conf`.
- Новый пакет использует:

  ```text
  /opt/etc/tg-ws-proxy/config.conf
  /opt/etc/tg-ws-proxy/secret.conf
  ```

- Во время установки пакет сгенерировал новый secret.
- Чтобы не сломать старую Telegram proxy-ссылку, старый `SECRET` был перенесен из `/opt/etc/tg-ws-proxy.conf-opkg.backup` в `/opt/etc/tg-ws-proxy/secret.conf`.
- Права на новый secret-файл выставлены в `600`.

Финальная проверка `tg-ws-proxy`:

```text
Package: tg-ws-proxy
Version: 0.7.2-1
Status: install user installed
Architecture: mipsel-3.4

S61tg-ws-proxy status: alive
Listening: :::1443
Process: /opt/bin/tg-ws-proxy --host 0.0.0.0 --port 1443 ...
```

Временный пакет оставлен на роутере:

```text
/opt/tmp/tg-ws-proxy_0.7.2-1_entware_mipsel-3.4.ipk
```

### Результат обновления Usque

Архив `usque_3.0.0_linux_mipsle.zip` был скачан локально, проверен по checksum, распакован, а бинарник `usque` загружен на роутер:

```text
/opt/tmp/usque-v3.0.0
```

Временный бинарник был проверен перед заменой:

```text
usque version: v3.0.0
Commit: 47c1b1bf2c8675d906bc8026515585ced27beef7
Build Date: 2026-04-21T23:57:34Z
```

Флаги, которые использует текущий init-скрипт, проверены через `usque socks --help`; они есть в новой версии:

```text
-b / --bind
-p / --port
-d / --dns
-s / --sni-address
-S / --no-tunnel-ipv6
```

Установленный бинарник:

```text
/opt/usr/bin/usque
```

Дополнительный бэкап старого бинарника:

```text
/opt/usr/bin/usque.v2.0.1.bak-20260530-140129
```

Финальная проверка Usque:

```text
usque version: v3.0.0
Commit: 47c1b1bf2c8675d906bc8026515585ced27beef7
Build Date: 2026-04-21T23:57:34Z

S99usque status: Usque SOCKS5 is stopped.
```

Usque был остановлен до обновления и намеренно оставлен остановленным после обновления.

Временный тестовый бинарник оставлен на роутере:

```text
/opt/tmp/usque-v3.0.0
```

## Состояние сразу после обновления

Финальная проверка после обновления, до отдельного запуска Usque:

```text
Sat May 30 14:01:56 MSK 2026
up 2 days, 15:38
load average: 0.34, 0.31, 0.23

tg-ws-proxy: 0.7.2-1, alive, listening on :::1443
Usque: v3.0.0, service stopped
```

## Запуск Usque - 2026-05-30

По отдельной команде Usque был запущен через init-скрипт:

```sh
/opt/etc/init.d/S99usque start
```

Перед стартом была подтверждена установленная версия:

```text
usque version: v3.0.0
Commit: 47c1b1bf2c8675d906bc8026515585ced27beef7
Build Date: 2026-04-21T23:57:34Z
```

Результат запуска:

```text
Checking LAN IP 192.168.1.1...
LAN IP is ready.
Checking internet connectivity...
Internet is reachable.
Checking DNS resolution for ozon.ru...
DNS is ready.
Starting Usque SOCKS5: done. (PID 30361)
```

Финальный статус после запуска:

```text
Usque SOCKS5 is running (PID 30361).
```

Процесс:

```text
/opt/usr/bin/usque socks -S -b 192.168.1.1 -p 8480 -d 1.1.1.1 -d 1.0.0.1 -s ozon.ru
```

Слушающие порты после запуска:

```text
tcp  192.168.1.1:8480  LISTEN  30361/usque
udp  192.168.1.1:8480          30361/usque
```

Текущее состояние после запуска:

```text
tg-ws-proxy: 0.7.2-1, alive, listening on :::1443
Usque: v3.0.0, running, listening on 192.168.1.1:8480 TCP/UDP
```

## Проверка автозапуска Usque - 2026-05-30

Usque подключен к автозапуску Entware.

Init-скрипт существует и является исполняемым:

```text
-rwxr-xr-x /opt/etc/init.d/S99usque
EXECUTABLE=1
```

`/opt/etc/init.d/rc.unslung` запускает все исполняемые скрипты `S*` из `/opt/etc/init.d` в порядке сортировки:

```sh
for i in $(/opt/bin/find /opt/etc/init.d/ -perm '-u+x' -name 'S*' | sort $ORDER ) ;
do
    ...
    . $i $ACTION $CALLER
done
```

Список `S*`-скриптов, среди которых есть Usque:

```text
S51dropbear
S51nfqws2
S61tg-ws-proxy
S80lighttpd
S80mosquitto
S99tuya-mqtt-calibrator
S99usque
```

Вывод: при штатном запуске Entware через `rc.unslung start` скрипт `/opt/etc/init.d/S99usque` будет запускаться автоматически. В самом скрипте Usque есть ожидание LAN IP, интернета и DNS перед стартом.

## Как откатиться

Точка отката для пакета/конфига `tg-ws-proxy`:

```sh
ls -la /opt/tmp/codex-update-backup-20260530-135709
ls -la /opt/etc/tg-ws-proxy.conf-opkg.backup
```

Откат бинарника Usque:

```sh
/opt/etc/init.d/S99usque stop
cp -a /opt/usr/bin/usque.v2.0.1.bak-20260530-140129 /opt/usr/bin/usque
chmod 755 /opt/usr/bin/usque
```

## Важное про HTTPS-фиды opkg

`opkg update` сейчас не может скачать HTTPS-only пользовательские фиды, потому что downloader, который использует `opkg`, сообщает:

```text
wget: not an http or ftp url: https://...
```

Основные HTTP-фиды Entware работают, но часть пользовательских HTTPS-фидов не обновляется.

Что можно отдельно проверить позже:

```sh
opkg list | grep -E '^wget|^ca-certificates|^libustream'
opkg install wget-ssl ca-certificates
```

Перед установкой нужно проверить наличие этих пакетов именно для текущего Entware target.
