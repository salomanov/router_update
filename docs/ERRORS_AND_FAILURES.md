# База знаний ошибок, граблей и неудачных экспериментов (FAILURE LOG)
> **Назначение файла**: Полный реестр всех ошибочных решений, тупиковых гипотез и проверенных антипаттернов.
> **Правило разработчика**: ПЕРЕД любым изменением пинов, регистров или архитектуры ОБЯЗАТЕЛЬНО свериться с этим файлом!

---


---

### [Инцидент 2026-11-25 21:46:12] Выездное обновление роутера (salomanov/router_update): 5 инцидентов автоустановщика
- **Симптом и ущерб**: 1) Instagram HTTP 000 (S99usque: not found); 2) Instagram HTTP 000 после установки usque (правила REDSOCKS_TG не применились); 3) Ложные HTTP 000 на YouTube и ChatGPT в самопроверке curl; 4) Падение GRouter Панели (ModuleNotFoundError: subprocess и libpython3.14.so.1.0 not found); 5) Ошибка PHP 8 в nfqws2-ui (inet_pton: Argument #1 must not contain any null bytes).
- **Причина (Root Cause)**: 1) 10_proxy_stack.sh не устанавливал бинарник usque и S99usque; 2) Прямой вызов 010-proxy.sh и 020-block-quic.sh без env-переменных table=nat / table=filter приводил к мгновенному выходу по NDM guard; 3) curl без -4 уходил в IPv6 AAAA YouTube, а без -I качал 500 КБ HTML ChatGPT до таймаута 8с; 4) В 07_dashboard.sh стоял python3-light, а установка python3 (3.14) поверх старого Entware (3.13) вызвала рассинхрон ABI с python3-base и libpython3; 5) После обрыва питания в файле /opt/etc/nfqws2/lists/* (auto.list) остались нулевые байты \x00.
- **Решение и правило**: 1) В 10_proxy_stack.sh добавлена автоустановка bin/usque-mipsel.gz + register -a + S99usque; 2) Вызовы NDM-хуков исправлены на table=nat / table=filter type=iptables; 3) Самопроверка в install.sh переведена на curl -4 -I --max-time 10; 4) В 07_dashboard.sh добавлена установка полного python3 и точечный opkg upgrade libpython3 python3-base python3-light python3-codecs python3-email python3-logging python3-urllib python3-openssl; 5) В 03_nfqws2.sh добавлена санация \x00 (tr -d '\0') для /opt/etc/nfqws2/lists/* и сброс кэша nfqws-ui.
