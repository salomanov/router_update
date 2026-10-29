// GRouter Control Center - Modernized Frontend
// State Management
let routerHost = "http://192.168.1.1:8089";
let isConnected = false;
let refreshIntervalId = null;
const REFRESH_RATE_MS = 6000; // Auto refresh every 6 seconds
let isRefreshPaused = false;
let pendingUpdate = null; // Store { service, version, url, isOpkg, command }

let lastServicesData = null;
let lastCatalogData = null;
let lastVersionsData = null;
let lastOpkgVersionsData = null;
let isUpstreamFetching = false;

// Command History State
let commandHistory = [];
let historyIndex = -1;

// Service Meta Information
const SERVICE_METADATA = {
    "ttyd": { name: "Web Terminal (ttyd / PuTTY)", desc: "Полноценный веб-терминал SSH/PuTTY в браузере", git: "https://github.com/tsl0922/ttyd" },
    "dropbear": { name: "SSH (Dropbear)", desc: "Сервер удаленного доступа SSH", git: "https://github.com/mkj/dropbear" },
    "nfqws2": { name: "nfqws2 (zapret)", desc: "Обход систем фильтрации DPI / zapret", git: "https://github.com/bol-van/zapret" },
    "tg-ws-proxy": { name: "tg-ws-proxy", desc: "Прокси Telegram MTProto WebSockets (Go)", git: "https://github.com/spatiumstas/tg-ws-proxy-go" },
    "mosquitto": { name: "Mosquitto MQTT", desc: "Брокер сообщений для умного дома", git: "https://github.com/eclipse-mosquitto/mosquitto" },
    "nfqws-web": { name: "Веб-интерфейс nfqws (Web UI)", desc: "Официальная веб-панель nfqws / zapret (порт 90)", git: "https://github.com/nfqws/nfqws-keenetic-web", port: 90 },
    "tuya-mqtt-calibrator": { name: "Tuya MQTT Calibrator", desc: "Калибратор Tuya датчиков" },
    "usque": { name: "Usque SOCKS5", desc: "SOCKS5 прокси-клиент", git: "https://github.com/Diniboy1123/usque" },
    "tailscale": { name: "Tailscale VPN", desc: "Mesh VPN / Exit Node для удаленного доступа", git: "https://github.com/tailscale/tailscale" },
    "3proxy": { name: "3proxy", desc: "Универсальный HTTPS/SOCKS5 прокси-сервер", git: "https://github.com/3proxy/3proxy" },
    "adguardhome": { name: "AdGuard Home", desc: "DNS-сервер блокировки рекламы и трекеров", git: "https://github.com/AdguardTeam/AdGuardHome" },
    "transmission": { name: "Transmission", desc: "Торрент-клиент с веб-интерфейсом", git: "https://github.com/transmission/transmission" },
    "stubby": { name: "Stubby DNS", desc: "Шифрование DNS-over-TLS (DoT)", git: "https://github.com/dnsprivacy/stubby" },
    "iperf3": { name: "iPerf3", desc: "Тестирование пропускной способности сети", git: "https://github.com/esnet/iperf" },
    "opds": { name: "NanoOPDS Library", desc: "Сверхлегкий OPDS-сервер электронных книг" }
};

// Upstream GitHub Releases Cache
const upstreamReleases = {
    "nfqws2": { repo: "nfqws/nfqws2-keenetic", keyword: ".ipk", latest: null, url: null, error: null },
    "nfqws-web": { repo: "nfqws/nfqws-keenetic-web", keyword: ".ipk", latest: null, url: null, error: null },
    "tg-ws-proxy": { repo: "spatiumstas/tg-ws-proxy-go", keyword: "mipsel-3.4.ipk", latest: null, url: null, error: null },
    "usque": { repo: "Diniboy1123/usque", keyword: "mipsle.zip", latest: null, url: null, error: null }
};

// DOM Elements
const hostInput = document.getElementById("router-host");
const btnConnect = document.getElementById("btn-connect");
const connectionStatus = document.getElementById("connection-status");
const btnRefresh = document.getElementById("btn-refresh");
const btnOpkgUpdate = document.getElementById("btn-opkg-update");
const servicesTbody = document.getElementById("services-tbody");
const consoleOutput = document.getElementById("console-output");
const btnClearConsole = document.getElementById("btn-clear-console");

// Auth Elements
const authHeaderSection = document.getElementById("auth-header-section");
const currentUserName = document.getElementById("current-user-name");
const btnLogout = document.getElementById("btn-logout");
const loginModal = document.getElementById("login-modal");
const loginForm = document.getElementById("login-form");
const loginUsernameInput = document.getElementById("login-username");
const loginPasswordInput = document.getElementById("login-password");
const loginErrorMsg = document.getElementById("login-error-msg");

// Tab Navigation Elements
const tabBtnInstalled = document.getElementById("tab-btn-installed");
const tabBtnCatalog = document.getElementById("tab-btn-catalog");
const tabBtnTerminal = document.getElementById("tab-btn-terminal");
const tabInstalledView = document.getElementById("tab-installed-view");
const tabCatalogView = document.getElementById("tab-catalog-view");
const tabTerminalView = document.getElementById("tab-terminal-view");
const installedCount = document.getElementById("installed-count");
const catalogCount = document.getElementById("catalog-count");
const catalogTbody = document.getElementById("catalog-tbody");

// Terminal Elements
const terminalIframe = document.getElementById("terminal-iframe");
const btnRestartTtyd = document.getElementById("btn-restart-ttyd");
const btnFullscreenTerminal = document.getElementById("btn-fullscreen-terminal");
const ttydStatusBadge = document.getElementById("ttyd-status-badge");

// Command Executor Elements
const cmdInput = document.getElementById("cmd-input");
const btnRunCmd = document.getElementById("btn-run-cmd");

// Modals
const helpModal = document.getElementById("help-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnModalOk = document.getElementById("btn-modal-ok");
const confirmModal = document.getElementById("confirm-modal");
const btnCloseConfirm = document.getElementById("btn-confirm-close");
const btnConfirmCancel = document.getElementById("btn-confirm-no");
const btnConfirmYes = document.getElementById("btn-confirm-yes");

// --- Token & Authentication Helpers ---

function getToken() {
    return localStorage.getItem("grouter_token") || "";
}

function setToken(token) {
    if (token) {
        localStorage.setItem("grouter_token", token);
    } else {
        localStorage.removeItem("grouter_token");
    }
}

function showLoginModal(errorText = "") {
    if (loginModal) {
        loginModal.classList.add("active");
        if (loginErrorMsg) {
            if (errorText) {
                loginErrorMsg.textContent = errorText;
                loginErrorMsg.style.display = "block";
            } else {
                loginErrorMsg.style.display = "none";
            }
        }
        if (loginPasswordInput) {
            loginPasswordInput.value = "";
            loginPasswordInput.focus();
        }
    }
}

function hideLoginModal() {
    if (loginModal) {
        loginModal.classList.remove("active");
    }
}

async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : `${routerHost}${endpoint}`;
    options.headers = options.headers || {};
    
    const token = getToken();
    if (token) {
        options.headers["Authorization"] = `Bearer ${token}`;
    }
    if (options.body && typeof options.body === "string" && !options.headers["Content-Type"]) {
        options.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, options);

    if (response.status === 401) {
        setToken("");
        updateAuthUI(false);
        showLoginModal("Требуется авторизация (admin:Salomanov)");
        throw new Error("Unauthorized (401)");
    }

    return response;
}

function updateAuthUI(isLoggedIn, username = "admin") {
    if (authHeaderSection) {
        authHeaderSection.style.display = isLoggedIn ? "flex" : "none";
        if (currentUserName) currentUserName.textContent = username;
    }
}

async function submitLogin(username, password) {
    try {
        logToConsole(`Попытка авторизации пользователя '${username}'...`);
        const resp = await fetch(`${routerHost}/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await resp.json();
        if (resp.ok && data.success && data.token) {
            setToken(data.token);
            hideLoginModal();
            updateAuthUI(true, data.username || username);
            logToConsole(`Успешная авторизация (${username})!`, "success");
            setConnectionState("online");
            startAutoRefresh();
            fetchRouterStatus(true);
            return true;
        } else {
            const err = data.error || "Неверный логин или пароль";
            showLoginModal(err);
            logToConsole(`Ошибка авторизации: ${err}`, "error");
            return false;
        }
    } catch (e) {
        showLoginModal(`Сетевая ошибка: ${e.message}`);
        logToConsole(`Сбой подключения при авторизации: ${e.message}`, "error");
        return false;
    }
}

function handleLogout() {
    logToConsole("Выход из системы...");
    apiRequest("/api/logout", { method: "POST", body: "{}" }).catch(() => {});
    setToken("");
    updateAuthUI(false);
    setConnectionState("offline");
    stopAutoRefresh();
    showLoginModal();
}

// --- Tab Navigation ---

function switchTab(targetTab) {
    if (tabBtnInstalled) tabBtnInstalled.classList.remove("active");
    if (tabBtnCatalog) tabBtnCatalog.classList.remove("active");
    if (tabBtnTerminal) tabBtnTerminal.classList.remove("active");

    if (tabInstalledView) tabInstalledView.style.display = "none";
    if (tabCatalogView) tabCatalogView.style.display = "none";
    if (tabTerminalView) tabTerminalView.style.display = "none";

    if (targetTab === "installed") {
        if (tabBtnInstalled) tabBtnInstalled.classList.add("active");
        if (tabInstalledView) tabInstalledView.style.display = "block";
    } else if (targetTab === "catalog") {
        if (tabBtnCatalog) tabBtnCatalog.classList.add("active");
        if (tabCatalogView) tabCatalogView.style.display = "block";
    } else if (targetTab === "terminal") {
        if (tabBtnTerminal) tabBtnTerminal.classList.add("active");
        if (tabTerminalView) tabTerminalView.style.display = "block";
        initTerminalView();
    }
}

function initTerminalView() {
    let host = window.location.hostname || "192.168.1.1";
    try {
        const u = new URL(routerHost);
        if (u.hostname) host = u.hostname;
    } catch (e) {}

    const terminalUrl = `http://${host}:7681/`;
    if (btnFullscreenTerminal) {
        btnFullscreenTerminal.href = terminalUrl;
    }
    const frame = document.getElementById("terminal-iframe") || terminalIframe;
    if (frame && (!frame.src || !frame.src.includes(":7681"))) {
        frame.src = terminalUrl;
    }
}

// --- Console Logger with Memory Bounds (Max 100 lines) ---

function logToConsole(message, type = "info") {
    if (!consoleOutput) return;
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    const timestamp = new Date().toLocaleTimeString();
    line.textContent = `[${timestamp}] ${message}`;
    consoleOutput.appendChild(line);
    
    // Cap at 100 lines to avoid DOM memory leaks
    while (consoleOutput.children.length > 100) {
        consoleOutput.removeChild(consoleOutput.firstChild);
    }
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearConsole() {
    if (consoleOutput) {
        consoleOutput.innerHTML = "";
        logToConsole("Консоль очищена.");
    }
}

function toggleModal(modal, show) {
    if (modal) {
        if (show) modal.classList.add("active");
        else modal.classList.remove("active");
    }
}

// --- Connection Handling ---

async function handleConnect() {
    if (btnConnect) btnConnect.disabled = true;
    routerHost = hostInput ? hostInput.value.trim().replace(/\/+$/, "") : routerHost;
    localStorage.setItem("grouter_host", routerHost);

    setConnectionState("loading");
    logToConsole(`Подключение к ${routerHost}...`);

    try {
        // If we don't have a token, prompt for login first
        if (!getToken()) {
            showLoginModal();
            setConnectionState("offline");
            if (btnConnect) btnConnect.disabled = false;
            return;
        }

        const authResp = await apiRequest("/api/auth/check");
        if (authResp.ok) {
            updateAuthUI(true, "admin");
            setConnectionState("online");
            startAutoRefresh();
            fetchRouterStatus(true);
            logToConsole("Успешно подключено к роутеру!", "success");
        }
    } catch (e) {
        if (e.message && e.message.includes("401")) {
            // Already handled in apiRequest
        } else {
            setConnectionState("offline");
            logToConsole(`Не удалось подключиться: ${e.message}`, "error");
            if (window.location.protocol === "https:" && routerHost.startsWith("http:")) {
                toggleModal(helpModal, true);
            }
        }
    } finally {
        if (btnConnect) btnConnect.disabled = false;
    }
}

function setConnectionState(state) {
    if (!connectionStatus) return;
    connectionStatus.className = `status-indicator ${state}`;
    const textEl = connectionStatus.querySelector(".status-text");
    if (state === "online") {
        isConnected = true;
        if (textEl) textEl.textContent = "В сети";
        if (btnConnect) {
            btnConnect.innerHTML = `<i class="fa-solid fa-plug-circle-check"></i> Подключено`;
            btnConnect.disabled = false;
        }
    } else if (state === "loading") {
        if (textEl) textEl.textContent = "Подключение...";
    } else {
        isConnected = false;
        if (textEl) textEl.textContent = "Не подключено";
        if (btnConnect) {
            btnConnect.innerHTML = `<i class="fa-solid fa-plug"></i> Подключиться`;
            btnConnect.disabled = false;
        }
    }
}

function startAutoRefresh() {
    stopAutoRefresh();
    refreshIntervalId = setInterval(() => {
        if (!isRefreshPaused && isConnected) {
            fetchRouterStatus(false);
        }
    }, REFRESH_RATE_MS);
}

function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
    }
}

function pauseAutoRefresh(durationMs = 60000) {
    isRefreshPaused = true;
    setTimeout(() => { isRefreshPaused = false; }, durationMs);
}

function resumeAutoRefresh() {
    isRefreshPaused = false;
}

// --- Fetch Router Status ---

async function fetchRouterStatus(force = false) {
    try {
        const resp = await apiRequest("/api/status");
        if (!resp.ok) return;
        const data = await resp.json();

        lastServicesData = data.services_detailed || convertLegacyServices(data.services);
        lastCatalogData = data.catalog || [];
        lastVersionsData = data.versions || {};
        lastOpkgVersionsData = data.opkg_versions || {};

        if (data.system) {
            renderSystemStats(data.system);
        }

        // Check ttyd status for badge
        const ttydService = lastServicesData.find(s => s.id === "ttyd");
        if (ttydStatusBadge) {
            if (ttydService && ttydService.status === "running") {
                ttydStatusBadge.className = "badge badge-success";
                ttydStatusBadge.innerHTML = `<i class="fa-solid fa-circle"></i> ttyd активен (порт 7681)`;
            } else {
                ttydStatusBadge.className = "badge badge-secondary";
                ttydStatusBadge.innerHTML = `<i class="fa-regular fa-circle"></i> ttyd остановлен`;
            }
        }

        await fetchUpstreamVersions();
        renderServicesTable(lastServicesData);
        renderCatalogTable(lastCatalogData);

    } catch (e) {
        if (!e.message || !e.message.includes("401")) {
            logToConsole(`Сбой получения статуса: ${e.message}`, "error");
        }
    }
}

function convertLegacyServices(servicesObj) {
    if (!servicesObj) return [];
    return Object.keys(servicesObj).map(id => {
        const meta = SERVICE_METADATA[id] || {};
        return {
            id,
            name: meta.name || id,
            desc: meta.desc || "",
            status: servicesObj[id],
            is_core: ["dropbear", "nfqws2", "tg-ws-proxy", "tailscale"].includes(id),
            package: id
        };
    });
}

function renderSystemStats(sys) {
    const cpuEl = document.getElementById("cpu-load");
    if (cpuEl) cpuEl.textContent = sys.cpu_load || "-- -- --";

    const ramFill = document.getElementById("ram-fill");
    const ramText = document.getElementById("ram-text");
    const ramPct = document.getElementById("ram-pct");

    if (sys.mem_total && sys.mem_total > 0) {
        const totalMb = Math.round(sys.mem_total / (1024 * 1024));
        const freeMb = Math.round(sys.mem_free / (1024 * 1024));
        const usedMb = Math.max(0, totalMb - freeMb);
        const pct = sys.mem_used_pct || Math.round((usedMb / totalMb) * 100);

        if (ramFill) ramFill.style.width = `${pct}%`;
        if (ramText) ramText.textContent = `${usedMb} / ${totalMb} MB`;
        if (ramPct) ramPct.textContent = `${pct}%`;
    }

    const diskFill = document.getElementById("disk-fill");
    const diskText = document.getElementById("disk-text");
    const diskPct = document.getElementById("disk-pct");

    if (sys.disk_used_pct !== undefined) {
        if (diskFill) diskFill.style.width = `${sys.disk_used_pct}%`;
        if (diskText) diskText.textContent = `${sys.disk_used} / ${sys.disk_total}`;
        if (diskPct) diskPct.textContent = `${sys.disk_used_pct}%`;
    }
}

// --- GitHub API Release Caching (Fix F1: 1-hour cache prevents rate limit) ---

async function fetchUpstreamVersions() {
    if (isUpstreamFetching) return;
    isUpstreamFetching = true;

    const CACHE_KEY = "grouter_github_cache";
    const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

    try {
        const cachedRaw = localStorage.getItem(CACHE_KEY);
        if (cachedRaw) {
            const cached = JSON.parse(cachedRaw);
            if (Date.now() - cached.timestamp < CACHE_TTL_MS && cached.data) {
                Object.keys(cached.data).forEach(s => {
                    if (upstreamReleases[s]) {
                        upstreamReleases[s].latest = cached.data[s].latest;
                        upstreamReleases[s].url = cached.data[s].url;
                    }
                });
                isUpstreamFetching = false;
                return;
            }
        }

        const cacheToSave = {};
        for (const [service, info] of Object.entries(upstreamReleases)) {
            try {
                const res = await fetch(`https://api.github.com/repos/${info.repo}/releases/latest`, {
                    headers: { "Accept": "application/vnd.github.v3+json" }
                });
                if (res.ok) {
                    const release = await res.json();
                    info.latest = release.tag_name;
                    const asset = release.assets?.find(a => a.name.includes(info.keyword));
                    info.url = asset ? asset.browser_download_url : null;
                    cacheToSave[service] = { latest: info.latest, url: info.url };
                }
            } catch (err) {
                // Ignore individual release check failure
            }
        }

        localStorage.setItem(CACHE_KEY, JSON.stringify({
            timestamp: Date.now(),
            data: cacheToSave
        }));

    } catch (e) {
        // Fallback silently if offline or blocked
    } finally {
        isUpstreamFetching = false;
    }
}

// --- Render Services Table ---

function renderServicesTable(services) {
    if (!servicesTbody) return;
    if (installedCount) installedCount.textContent = services.length;

    if (services.length === 0) {
        servicesTbody.innerHTML = `<tr><td colspan="5" class="empty-state">Нет установленных служб</td></tr>`;
        return;
    }

    servicesTbody.innerHTML = "";

    services.forEach(svc => {
        const tr = document.createElement("tr");

        // Service Name & Desc
        const tdName = document.createElement("td");
        tdName.innerHTML = `<strong>${escapeHtml(svc.name)}</strong><br><small style="color:var(--text-secondary)">${escapeHtml(svc.desc)}</small>`;

        // Status Badge
        const tdStatus = document.createElement("td");
        const isRunning = svc.status === "running";
        tdStatus.innerHTML = `<span class="badge ${isRunning ? "badge-success" : "badge-secondary"}"><i class="fa-solid fa-circle"></i> ${isRunning ? "Работает" : "Остановлен"}</span>`;

        // Current Version
        const tdVer = document.createElement("td");
        const curVer = lastVersionsData[svc.id] || "установлен";
        tdVer.innerHTML = `<code>${escapeHtml(curVer)}</code>`;

        // Set data-labels for mobile responsive cards
        tdName.setAttribute("data-label", "Служба");
        tdStatus.setAttribute("data-label", "Статус");
        tdVer.setAttribute("data-label", "Установлено");

        // Available Version
        const tdAvail = document.createElement("td");
        tdAvail.setAttribute("data-label", "В репозитории");

        let availVer = "--";
        let isUpdate = false;
        let updateUrl = null;

        if (upstreamReleases[svc.id] && upstreamReleases[svc.id].latest) {
            availVer = upstreamReleases[svc.id].latest;
            updateUrl = upstreamReleases[svc.id].url;
            if (curVer !== "unknown" && curVer !== availVer && curVer.replace(/^v/, "") !== availVer.replace(/^v/, "")) {
                isUpdate = true;
            }
        }
        
        if (availVer === "--" && svc.package) {
            const pkgKey = svc.package.split(" ")[0];
            if (lastOpkgVersionsData && lastOpkgVersionsData[pkgKey]) {
                availVer = lastOpkgVersionsData[pkgKey];
                if (curVer !== "unknown" && curVer !== availVer) {
                    isUpdate = true;
                }
            }
        }
        tdAvail.innerHTML = isUpdate ? `<span class="badge badge-warning" title="Доступно обновление"><i class="fa-solid fa-arrow-up"></i> ${escapeHtml(availVer)}</span>` : `<span style="color:var(--text-secondary)">${escapeHtml(availVer)}</span>`;

        // Actions
        const tdActions = document.createElement("td");
        tdActions.setAttribute("data-label", "Действия");
        const btnGroup = document.createElement("div");
        btnGroup.className = "btn-group";

        if (svc.port) {
            const host = window.location.hostname || "192.168.1.1";
            btnGroup.innerHTML += `<a href="http://${host}:${svc.port}/" target="_blank" class="btn btn-secondary btn-xs action-btn" title="Открыть веб-интерфейс (порт ${svc.port})"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>`;
        }

        if (isRunning) {
            btnGroup.innerHTML += `<button class="btn btn-secondary btn-xs action-btn" data-action="restart" data-svc="${svc.id}" title="Перезапустить"><i class="fa-solid fa-rotate-right"></i></button>`;
            btnGroup.innerHTML += `<button class="btn btn-secondary btn-xs action-btn" data-action="stop" data-svc="${svc.id}" title="Остановить"><i class="fa-solid fa-stop"></i></button>`;
        } else {
            btnGroup.innerHTML += `<button class="btn btn-primary btn-xs action-btn" data-action="start" data-svc="${svc.id}" title="Запустить"><i class="fa-solid fa-play"></i></button>`;
        }

        if (isUpdate) {
            btnGroup.innerHTML += `<button class="btn btn-warning btn-xs update-btn" data-svc="${svc.id}" data-ver="${availVer}" data-url="${updateUrl || ""}" title="Обновить"><i class="fa-solid fa-cloud-arrow-down"></i></button>`;
        }

        if (svc.can_uninstall) {
            btnGroup.innerHTML += `<button class="btn btn-danger btn-xs uninstall-btn" data-svc="${svc.id}" title="Удалить службу"><i class="fa-solid fa-trash-can"></i></button>`;
        }

        tdActions.appendChild(btnGroup);

        tr.appendChild(tdName);
        tr.appendChild(tdStatus);
        tr.appendChild(tdVer);
        tr.appendChild(tdAvail);
        tr.appendChild(tdActions);

        servicesTbody.appendChild(tr);
    });

    // Attach event listeners
    servicesTbody.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", () => controlService(btn.dataset.svc, btn.dataset.action));
    });

    servicesTbody.querySelectorAll(".update-btn").forEach(btn => {
        btn.addEventListener("click", () => triggerUpdate(btn.dataset.svc, btn.dataset.ver, btn.dataset.url));
    });

    servicesTbody.querySelectorAll(".uninstall-btn").forEach(btn => {
        btn.addEventListener("click", () => triggerUninstall(btn.dataset.svc));
    });
}

// --- Render Catalog Table ---

function renderCatalogTable(catalog) {
    if (!catalogTbody) return;
    if (catalogCount) catalogCount.textContent = catalog.length;

    if (catalog.length === 0) {
        catalogTbody.innerHTML = `<tr><td colspan="4" class="empty-state">Все доступные службы уже установлены</td></tr>`;
        return;
    }

    catalogTbody.innerHTML = "";

    catalog.forEach(item => {
        const tr = document.createElement("tr");

        const tdName = document.createElement("td");
        tdName.innerHTML = `<strong>${escapeHtml(item.name)}</strong>`;

        const tdDesc = document.createElement("td");
        tdDesc.textContent = item.desc || "";

        const tdVer = document.createElement("td");
        const v = (item.package && lastOpkgVersionsData[item.package]) || "OPKG репозиторий";
        tdVer.innerHTML = `<code>${escapeHtml(v)}</code>`;

        const tdAction = document.createElement("td");
        const btn = document.createElement("button");
        btn.className = "btn btn-primary btn-sm";
        btn.innerHTML = `<i class="fa-solid fa-download"></i> Установить`;
        btn.addEventListener("click", () => triggerCatalogInstall(item.id, item.install_cmd));
        tdAction.appendChild(btn);

        tr.appendChild(tdName);
        tr.appendChild(tdDesc);
        tr.appendChild(tdVer);
        tr.appendChild(tdAction);

        catalogTbody.appendChild(tr);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- Actions & Control ---

async function controlService(service, action) {
    logToConsole(`Выполнение: ${action} службы ${service}...`);
    pauseAutoRefresh(15000);
    try {
        const resp = await apiRequest("/api/service", {
            method: "POST",
            body: JSON.stringify({ service, action })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            logToConsole(`Служба ${service}: успешно выполнено ${action}`, "success");
        } else {
            logToConsole(`Ошибка действия ${action} для ${service}: ${data.error || data.output || "Неизвестная ошибка"}`, "error");
        }
        await fetchRouterStatus(true);
    } catch (e) {
        logToConsole(`Сетевой сбой при управлении службой: ${e.message}`, "error");
    } finally {
        resumeAutoRefresh();
    }
}

async function triggerCatalogInstall(serviceId, customCmd) {
    logToConsole(`Запуск установки ${serviceId}...`);
    pauseAutoRefresh(60000);
    try {
        const resp = await apiRequest("/api/service", {
            method: "POST",
            body: JSON.stringify({ service: serviceId, action: "install", install_cmd: customCmd })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            logToConsole(`Служба ${serviceId} успешно установлена!`, "success");
        } else {
            logToConsole(`Ошибка установки ${serviceId}: ${data.error || data.output}`, "error");
        }
        await fetchRouterStatus(true);
    } catch (e) {
        logToConsole(`Ошибка при отправке запроса установки: ${e.message}`, "error");
    } finally {
        resumeAutoRefresh();
    }
}

async function triggerUninstall(serviceId) {
    if (!confirm(`Вы действительно хотите удалить службу ${serviceId}?`)) return;
    logToConsole(`Удаление службы ${serviceId}...`);
    pauseAutoRefresh(30000);
    try {
        const resp = await apiRequest("/api/service", {
            method: "POST",
            body: JSON.stringify({ service: serviceId, action: "uninstall" })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            logToConsole(`Служба ${serviceId} успешно удалена`, "success");
        } else {
            logToConsole(`Ошибка при удалении ${serviceId}: ${data.error || data.output}`, "error");
        }
        await fetchRouterStatus(true);
    } catch (e) {
        logToConsole(`Сбой удаления: ${e.message}`, "error");
    } finally {
        resumeAutoRefresh();
    }
}

function triggerUpdate(service, version, url) {
    pendingUpdate = { service, version, url };
    const textEl = document.getElementById("confirm-modal-text");
    const detEl = document.getElementById("confirm-modal-details");
    if (textEl) textEl.textContent = `Обновить службу ${service} до версии ${version}?`;
    if (detEl) detEl.textContent = url ? `Источник: ${url}` : "Источник: репозиторий OPKG";
    toggleModal(confirmModal, true);
}

async function executePendingUpdate() {
    toggleModal(confirmModal, false);
    if (!pendingUpdate) return;
    const { service, version, url } = pendingUpdate;
    logToConsole(`Запуск обновления ${service} до ${version}...`);
    pauseAutoRefresh(60000);
    try {
        const resp = await apiRequest("/api/update", {
            method: "POST",
            body: JSON.stringify({ service, version, url })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            logToConsole(`Обновление ${service} успешно завершено!`, "success");
        } else {
            logToConsole(`Ошибка обновления ${service}: ${data.error || data.output}`, "error");
        }
        await fetchRouterStatus(true);
    } catch (e) {
        logToConsole(`Сбой обновления: ${e.message}`, "error");
    } finally {
        resumeAutoRefresh();
        pendingUpdate = null;
    }
}

// --- Quick Command Execution ---

async function runManualCommand(cmd) {
    if (!cmd) cmd = cmdInput ? cmdInput.value.trim() : "";
    if (!cmd) return;

    // Add to history
    if (!commandHistory.includes(cmd)) {
        commandHistory.push(cmd);
        if (commandHistory.length > 50) commandHistory.shift();
    }
    historyIndex = commandHistory.length;

    logToConsole(`> ${cmd}`, "system");
    if (cmdInput) cmdInput.value = "";
    if (btnRunCmd) btnRunCmd.disabled = true;

    pauseAutoRefresh(30000);
    try {
        const resp = await apiRequest("/api/exec", {
            method: "POST",
            body: JSON.stringify({ command: cmd, timeout: 120 })
        });
        const data = await resp.json();
        if (resp.ok) {
            const out = data.output ? data.output.trim() : "[Нет вывода]";
            logToConsole(out, data.success ? "info" : "error");
        } else {
            logToConsole(`Ошибка: ${data.error || "Сбой команды"}`, "error");
        }
    } catch (e) {
        logToConsole(`Ошибка выполнения команды: ${e.message}`, "error");
    } finally {
        if (btnRunCmd) btnRunCmd.disabled = false;
        resumeAutoRefresh();
    }
}

// --- Event Listeners Initialization ---

document.addEventListener("DOMContentLoaded", () => {
    // Automatically bind to current origin if served over HTTP/HTTPS
    if (window.location.origin && window.location.origin.startsWith("http")) {
        routerHost = window.location.origin;
        if (hostInput) hostInput.value = routerHost;
    } else {
        const savedHost = localStorage.getItem("grouter_host");
        if (savedHost && hostInput) {
            hostInput.value = savedHost;
            routerHost = savedHost;
        }
    }

    // Connect button
    if (btnConnect) btnConnect.addEventListener("click", handleConnect);
    if (btnRefresh) btnRefresh.addEventListener("click", () => fetchRouterStatus(true));
    if (btnClearConsole) btnClearConsole.addEventListener("click", clearConsole);
    if (btnLogout) btnLogout.addEventListener("click", handleLogout);

    // Opkg update button
    if (btnOpkgUpdate) {
        btnOpkgUpdate.addEventListener("click", () => runManualCommand("opkg update"));
    }

    // Quick command buttons
    document.querySelectorAll(".quick-cmd-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const cmd = btn.dataset.cmd;
            if (cmd) runManualCommand(cmd);
        });
    });

    // Run command input & keyboard
    if (btnRunCmd) btnRunCmd.addEventListener("click", () => runManualCommand());
    if (cmdInput) {
        cmdInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                runManualCommand();
            } else if (e.key === "ArrowUp") {
                if (commandHistory.length > 0 && historyIndex > 0) {
                    historyIndex--;
                    cmdInput.value = commandHistory[historyIndex];
                }
                e.preventDefault();
            } else if (e.key === "ArrowDown") {
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    cmdInput.value = commandHistory[historyIndex];
                } else {
                    historyIndex = commandHistory.length;
                    cmdInput.value = "";
                }
                e.preventDefault();
            }
        });
    }

    // Tab buttons
    if (tabBtnInstalled) tabBtnInstalled.addEventListener("click", () => switchTab("installed"));
    if (tabBtnCatalog) tabBtnCatalog.addEventListener("click", () => switchTab("catalog"));
    if (tabBtnTerminal) tabBtnTerminal.addEventListener("click", () => switchTab("terminal"));

    // Terminal restart button
    if (btnRestartTtyd) {
        btnRestartTtyd.addEventListener("click", async () => {
            await controlService("ttyd", "restart");
            setTimeout(() => {
                if (terminalIframe) {
                    const src = terminalIframe.src;
                    terminalIframe.src = "about:blank";
                    setTimeout(() => { terminalIframe.src = src; }, 500);
                }
            }, 2500);
        });
    }

    // Login Form Submit
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const u = loginUsernameInput ? loginUsernameInput.value.trim() : "admin";
            const p = loginPasswordInput ? loginPasswordInput.value.trim() : "";
            submitLogin(u, p);
        });
    }

    // Modals
    if (btnCloseModal) btnCloseModal.addEventListener("click", () => toggleModal(helpModal, false));
    if (btnModalOk) btnModalOk.addEventListener("click", () => toggleModal(helpModal, false));
    if (btnCloseConfirm) btnCloseConfirm.addEventListener("click", () => toggleModal(confirmModal, false));
    if (btnConfirmCancel) btnConfirmCancel.addEventListener("click", () => toggleModal(confirmModal, false));
    if (btnConfirmYes) btnConfirmYes.addEventListener("click", executePendingUpdate);

    // Initial check: if token exists, try connecting immediately
    if (getToken()) {
        handleConnect();
    } else {
        // Show login modal on initial load so user can enter admin / Salomanov
        showLoginModal();
    }
});
