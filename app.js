// State Management
let routerHost = "http://192.168.1.1:8089";
let isConnected = false;
let refreshIntervalId = null;
const REFRESH_RATE_MS = 6000; // Auto refresh every 6 seconds
let isRefreshPaused = false;
let pendingUpdate = null; // Store { service, version, url, isOpkg, command }

// Service Meta Information
const SERVICE_METADATA = {
    "dropbear": { name: "SSH (Dropbear)", desc: "Сервер удаленного доступа SSH", git: "https://github.com/mkj/dropbear" },
    "nfqws2": { name: "nfqws2 (zapret)", desc: "Обход систем фильтрации DPI / zapret", git: "https://github.com/bol-van/zapret" },
    "tg-ws-proxy": { name: "tg-ws-proxy", desc: "Прокси Telegram MTProto WebSockets (Go)", git: "https://github.com/spatiumstas/tg-ws-proxy-go" },
    "mosquitto": { name: "Mosquitto MQTT", desc: "Брокер сообщений для умного дома", git: "https://github.com/eclipse-mosquitto/mosquitto" },
    "lighttpd": { name: "Lighttpd", desc: "Веб-сервер роутера", git: "https://github.com/lighttpd/lighttpd1.4" },
    "tuya-mqtt-calibrator": { name: "Tuya MQTT Calibrator", desc: "Калибратор Tuya датчиков" },
    "usque": { name: "Usque SOCKS5", desc: "SOCKS5 прокси-клиент", git: "https://github.com/Diniboy1123/usque" }
};

// Upstream GitHub Releases Cache
const upstreamReleases = {
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

// Command Executor Elements
const cmdInput = document.getElementById("cmd-input");
const btnRunCmd = document.getElementById("btn-run-cmd");

// Modal Elements
const helpModal = document.getElementById("help-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnModalOk = document.getElementById("btn-modal-ok");

// Confirm Modal Elements
const confirmModal = document.getElementById("confirm-modal");
const btnCloseConfirm = document.getElementById("btn-close-confirm");
const btnConfirmCancel = document.getElementById("btn-confirm-cancel");
const btnConfirmYes = document.getElementById("btn-confirm-yes");

// Init
window.addEventListener("DOMContentLoaded", () => {
    // Load saved host if any
    const savedHost = localStorage.getItem("router_host");
    if (savedHost) {
        routerHost = savedHost;
        hostInput.value = savedHost;
    }
    
    // Bind Event Listeners
    btnConnect.addEventListener("click", handleConnect);
    btnRefresh.addEventListener("click", () => fetchRouterStatus(true));
    btnOpkgUpdate.addEventListener("click", runOpkgUpdate);
    btnClearConsole.addEventListener("click", clearConsole);
    
    // Manual Command Executor
    btnRunCmd.addEventListener("click", runManualCommand);
    cmdInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            runManualCommand();
        }
    });
    
    // Modal events
    btnCloseModal.addEventListener("click", toggleModal);
    btnModalOk.addEventListener("click", toggleModal);
    
    // Confirm Modal events
    btnCloseConfirm.addEventListener("click", handleConfirmCancel);
    btnConfirmCancel.addEventListener("click", handleConfirmCancel);
    btnConfirmYes.addEventListener("click", handleConfirmYes);
    
    // Pre-fetch upstream versions in background
    fetchUpstreamVersions();
});

// Logs helper
function logToConsole(source, text, type = "output") {
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    
    const time = new Date().toLocaleTimeString();
    line.textContent = `[${time}] [${source}] ${text}`;
    
    consoleOutput.appendChild(line);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearConsole() {
    consoleOutput.innerHTML = '<div class="console-line system">[Система] Консоль очищена.</div>';
}

function toggleModal() {
    helpModal.classList.toggle("active");
}

// Check if current site is HTTPS and target host is HTTP (triggers Mixed Content warning)
function isMixedContentConflict(url) {
    const isHttpsPage = window.location.protocol === "https:";
    const isHttpTarget = url.startsWith("http://");
    return isHttpsPage && isHttpTarget;
}

// Connect Action
async function handleConnect() {
    let host = hostInput.value.trim();
    if (!host) return;
    
    // Auto-fix slash at the end
    if (host.endsWith("/")) {
        host = host.slice(0, -1);
    }
    
    routerHost = host;
    localStorage.setItem("router_host", routerHost);
    
    logToConsole("Система", `Подключение к ${routerHost}...`, "system");
    
    setConnectionState("loading");
    
    await fetchRouterStatus(false);
}

function setConnectionState(state) {
    connectionStatus.className = `status-indicator ${state}`;
    const dot = connectionStatus.querySelector(".dot");
    const statusText = connectionStatus.querySelector(".status-text");
    
    if (state === "online") {
        isConnected = true;
        statusText.textContent = "В сети";
        btnConnect.innerHTML = '<i class="fa-solid fa-link-slash"></i> Отключить';
        btnConnect.className = "btn btn-secondary";
        
        // Start auto-refresh
        if (!refreshIntervalId) {
            refreshIntervalId = setInterval(() => {
                if (!isRefreshPaused) {
                    fetchRouterStatus(true);
                }
            }, REFRESH_RATE_MS);
        }
    } else if (state === "loading") {
        statusText.textContent = "Подключение...";
        btnConnect.disabled = true;
    } else {
        isConnected = false;
        statusText.textContent = "Не подключен";
        btnConnect.innerHTML = '<i class="fa-solid fa-plug"></i> Подключить';
        btnConnect.className = "btn btn-primary";
        btnConnect.disabled = false;
        
        // Stop auto-refresh
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
            refreshIntervalId = null;
        }
    }
}

// Fetch Status from Router
async function fetchRouterStatus(isRefresh = false) {
    try {
        const response = await fetch(`${routerHost}/api/status`, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            },
            mode: "cors"
        });
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!isConnected) {
            logToConsole("Система", "Успешно подключено к роутеру!", "success");
        }
        setConnectionState("online");
        
        renderSystemStats(data.system);
        renderServicesTable(data.services, data.versions, data.opkg_versions);
        
    } catch (err) {
        console.error(err);
        
        if (isRefresh) {
            logToConsole("Система", `Ошибка автообновления: ${err.message}`, "error");
        } else {
            logToConsole("Система", `Не удалось подключиться к роутеру. ${err.message}`, "error");
            setConnectionState("offline");
            
            // Check if this looks like a Mixed Content blocking issue
            if (isMixedContentConflict(routerHost)) {
                logToConsole("Безопасность", "Запрос был заблокирован браузером из-за Mixed Content (HTTPS -> HTTP).", "error");
                toggleModal(); // Show instructional modal
            } else {
                logToConsole("Подсказка", "Проверьте, запущен ли API-сервер на роутере и правильно ли указан IP-адрес / порт.", "system");
            }
        }
    }
}

// Render System Stats
function renderSystemStats(system) {
    if (!system) return;
    
    // CPU
    document.getElementById("cpu-load").textContent = system.cpu_load || "-- -- --";
    
    // RAM
    const ramPct = system.mem_used_pct || 0;
    const ramFill = document.getElementById("ram-fill");
    ramFill.style.width = `${ramPct}%`;
    
    const ramTotalMb = Math.round(system.mem_total / (1024 * 1024)) || 0;
    const ramUsedMb = Math.round((system.mem_total - system.mem_free) / (1024 * 1024)) || 0;
    document.getElementById("ram-text").textContent = `${ramUsedMb} / ${ramTotalMb} MB`;
    document.getElementById("ram-pct").textContent = `${ramPct}%`;
    
    // Disk
    const diskPct = system.disk_used_pct || 0;
    const diskFill = document.getElementById("disk-fill");
    diskFill.style.width = `${diskPct}%`;
    document.getElementById("disk-text").textContent = `${system.disk_used || '--'} / ${system.disk_total || '--'}`;
    document.getElementById("disk-pct").textContent = `${diskPct}%`;
}

// Fetch Latest Releases from GitHub in background
async function fetchUpstreamVersions() {
    for (const key in upstreamReleases) {
        const item = upstreamReleases[key];
        try {
            const res = await fetch(`https://api.github.com/repos/${item.repo}/releases/latest`);
            if (!res.ok) throw new Error(`GitHub API Error: ${res.status}`);
            
            const data = await res.json();
            const tag = data.tag_name;
            
            // Find correct asset matching the platform
            const asset = data.assets.find(a => a.name.toLowerCase().includes(item.keyword));
            if (asset) {
                item.latest = tag;
                item.url = asset.browser_download_url;
            } else {
                item.latest = tag;
                item.url = null; // Could not find matching asset
                item.error = "Asset not found for platform";
            }
        } catch (e) {
            console.error(`Failed to fetch upstream for ${key}:`, e);
            item.error = e.message;
        }
    }
    
    // If we're already connected, redraw table to display updates
    if (isConnected) {
        fetchRouterStatus(true);
    }
}

// Compare versions to check if update is available
function isUpdateAvailable(installed, latest) {
    if (!installed || installed === "unknown" || installed === "not installed" || !latest) return false;
    
    // Strip leading 'v'
    const cleanInstalled = installed.replace(/^v/, "").split("-")[0]; // e.g. "0.7.2-1" -> "0.7.2"
    const cleanLatest = latest.replace(/^v/, "").split("-")[0];
    
    if (cleanInstalled === cleanLatest) return false;
    
    // Compare versions split by dots
    const partsInst = cleanInstalled.split(".").map(Number);
    const partsLat = cleanLatest.split(".").map(Number);
    
    for (let i = 0; i < Math.max(partsInst.length, partsLat.length); i++) {
        const vInst = partsInst[i] || 0;
        const vLat = partsLat[i] || 0;
        if (vLat > vInst) return true;
        if (vLat < vInst) return false;
    }
    
    return false;
}

// Render Services list
function renderServicesTable(services, versions, opkgVersions) {
    if (!services) return;
    
    servicesTbody.innerHTML = "";
    
    for (const key in SERVICE_METADATA) {
        const meta = SERVICE_METADATA[key];
        const status = services[key] || "unknown";
        const installedVersion = versions ? versions[key] : null;
        const opkgVersion = opkgVersions ? opkgVersions[key] : null;
        
        const tr = document.createElement("tr");
        tr.setAttribute("data-service", key);
        
        // Name Column (with Git icon link if configured)
        const tdName = document.createElement("td");
        tdName.className = "service-name";
        
        let gitLinkHtml = "";
        if (meta.git) {
            gitLinkHtml = ` <a href="${meta.git}" target="_blank" class="git-link" title="Перейти на GitHub"><i class="fa-brands fa-github"></i></a>`;
        }
        
        tdName.innerHTML = `<strong>${meta.name}${gitLinkHtml}</strong><span class="service-desc">${meta.desc}</span>`;
        tr.appendChild(tdName);
        
        // Status Badge Column
        const tdStatus = document.createElement("td");
        let badgeHtml = "";
        if (status === "running") {
            badgeHtml = `<span class="badge running"><i class="fa-solid fa-circle"></i> Запущен</span>`;
        } else if (status === "stopped") {
            badgeHtml = `<span class="badge stopped"><i class="fa-solid fa-circle"></i> Остановлен</span>`;
        } else {
            badgeHtml = `<span class="badge unknown"><i class="fa-solid fa-circle"></i> Неизвестно</span>`;
        }
        tdStatus.innerHTML = badgeHtml;
        tr.appendChild(tdStatus);
        
        // Installed Version Column
        const tdVersion = document.createElement("td");
        tdVersion.className = "version-cell";
        tdVersion.textContent = installedVersion || "—";
        tr.appendChild(tdVersion);
        
        // Release Column (OPKG or GitHub)
        const tdGitHub = document.createElement("td");
        tdGitHub.className = "version-cell";
        
        const upstream = upstreamReleases[key];
        if (upstream) {
            // This service is configured to check GitHub releases
            if (upstream.error) {
                tdGitHub.innerHTML = `<span class="text-muted" title="${upstream.error}"><i class="fa-solid fa-triangle-exclamation"></i> Ошибка GitHub</span>`;
            } else if (upstream.latest) {
                const hasUpdate = isUpdateAvailable(installedVersion, upstream.latest);
                if (hasUpdate) {
                    tdGitHub.textContent = `${upstream.latest} `;
                    
                    const badgeUpdate = document.createElement("span");
                    badgeUpdate.className = "badge-update warning";
                    badgeUpdate.title = "Нажмите, чтобы обновить через GitHub";
                    badgeUpdate.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> GitHub`;
                    badgeUpdate.onclick = () => triggerUpdate(key, upstream.latest, upstream.url);
                    tdGitHub.appendChild(badgeUpdate);
                } else {
                    const badgeUpToDate = document.createElement("span");
                    badgeUpToDate.className = "badge-update success";
                    badgeUpToDate.innerHTML = `<i class="fa-solid fa-check"></i> Актуально`;
                    tdGitHub.textContent = `${upstream.latest} `;
                    tdGitHub.appendChild(badgeUpToDate);
                }
            } else {
                tdGitHub.innerHTML = `<span class="badge-update loading"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка GitHub...</span>`;
            }
        } else if (opkgVersion) {
            // This service is a standard OPKG package and has a version in the repository
            const hasUpdate = isUpdateAvailable(installedVersion, opkgVersion);
            if (hasUpdate) {
                tdGitHub.textContent = `${opkgVersion} `;
                
                const badgeUpdate = document.createElement("span");
                badgeUpdate.className = "badge-update warning";
                badgeUpdate.title = "Нажмите, чтобы обновить через OPKG";
                badgeUpdate.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> OPKG`;
                badgeUpdate.onclick = () => triggerOpkgUpgrade(key, opkgVersion);
                tdGitHub.appendChild(badgeUpdate);
            } else {
                const badgeUpToDate = document.createElement("span");
                badgeUpToDate.className = "badge-update success";
                badgeUpToDate.innerHTML = `<i class="fa-solid fa-check"></i> Актуально`;
                tdGitHub.textContent = `${opkgVersion} `;
                tdGitHub.appendChild(badgeUpToDate);
            }
        } else {
            tdGitHub.innerHTML = `<span class="text-muted">—</span>`;
        }
        tr.appendChild(tdGitHub);
        
        // Actions Column
        const tdActions = document.createElement("td");
        tdActions.className = "actions-cell";
        
        if (status === "running") {
            const btnStop = document.createElement("button");
            btnStop.className = "btn-action stop";
            btnStop.title = "Остановить";
            btnStop.innerHTML = `<i class="fa-solid fa-stop"></i>`;
            btnStop.onclick = () => controlService(key, 'stop');
            
            const btnRestart = document.createElement("button");
            btnRestart.className = "btn-action restart";
            btnRestart.title = "Перезапустить";
            btnRestart.innerHTML = `<i class="fa-solid fa-arrow-rotate-right"></i>`;
            btnRestart.onclick = () => controlService(key, 'restart');
            
            tdActions.appendChild(btnStop);
            tdActions.appendChild(btnRestart);
        } else if (status === "stopped") {
            const btnStart = document.createElement("button");
            btnStart.className = "btn-action start";
            btnStart.title = "Запустить";
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i>`;
            btnStart.onclick = () => controlService(key, 'start');
            
            tdActions.appendChild(btnStart);
        } else {
            const btnStart = document.createElement("button");
            btnStart.className = "btn-action start";
            btnStart.title = "Запустить";
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i>`;
            btnStart.onclick = () => controlService(key, 'start');
            
            const btnStop = document.createElement("button");
            btnStop.className = "btn-action stop";
            btnStop.title = "Остановить";
            btnStop.innerHTML = `<i class="fa-solid fa-stop"></i>`;
            btnStop.onclick = () => controlService(key, 'stop');
            
            tdActions.appendChild(btnStart);
            tdActions.appendChild(btnStop);
        }
        
        // Add Upgrade button directly in action column if update is available
        const hasGithubUpdate = upstream && upstream.latest && isUpdateAvailable(installedVersion, upstream.latest) && upstream.url;
        const hasOpkgUpdate = !upstream && opkgVersion && isUpdateAvailable(installedVersion, opkgVersion);
        
        if (hasGithubUpdate) {
            const updateBtn = document.createElement("button");
            updateBtn.className = "btn-upgrade";
            updateBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Обновить до ${upstream.latest}`;
            updateBtn.onclick = () => triggerUpdate(key, upstream.latest, upstream.url);
            tdActions.appendChild(updateBtn);
        } else if (hasOpkgUpdate) {
            const updateBtn = document.createElement("button");
            updateBtn.className = "btn-upgrade";
            updateBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Обновить до ${opkgVersion}`;
            updateBtn.onclick = () => triggerOpkgUpgrade(key, opkgVersion);
            tdActions.appendChild(updateBtn);
        }
        
        tr.appendChild(tdActions);
        servicesTbody.appendChild(tr);
    }
}

// Control Service Actions (Start / Stop / Restart)
async function controlService(service, action) {
    if (!isConnected) return;
    
    logToConsole(service, `Запрос на ${action}...`, "cmd");
    
    try {
        const response = await fetch(`${routerHost}/api/service`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ service, action }),
            mode: "cors"
        });
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            logToConsole(service, `Успешно: ${action}. Статус: ${result.new_status}`, "success");
            if (result.output) {
                logToConsole(service, result.output, "output");
            }
        } else {
            logToConsole(service, `Ошибка выполнения: ${result.output || 'Неизвестная ошибка'}`, "error");
        }
        
        // Immediately refresh status
        fetchRouterStatus(true);
        
    } catch (e) {
        logToConsole(service, `Сбой запроса: ${e.message}`, "error");
    }
}

// Trigger Service Update (GitHub)
async function triggerUpdate(service, version, url) {
    if (!isConnected) return;
    
    pendingUpdate = { service, version, url, isOpkg: false };
    
    // Setup modal text
    const confirmModalText = document.getElementById("confirm-modal-text");
    confirmModalText.innerHTML = `Вы уверены, что хотите обновить сервис <strong>${service}</strong> до версии <strong>${version}</strong> с GitHub?<br><span style="font-size: 11px; color: var(--text-muted); word-break: break-all;">${url}</span>`;
    
    // Show Modal
    confirmModal.classList.add("active");
    pauseAutoRefresh();
}

// Trigger OPKG Service Update
async function triggerOpkgUpgrade(service, version) {
    if (!isConnected) return;
    
    const opkgNameMap = {
        "mosquitto": "mosquitto-ssl",
        "lighttpd": "lighttpd",
        "dropbear": "dropbear",
        "nfqws2": "nfqws2-keenetic",
        "tg-ws-proxy": "tg-ws-proxy"
    };
    
    const packageName = opkgNameMap[service];
    if (!packageName) return;
    
    pendingUpdate = {
        service,
        version,
        isOpkg: true,
        command: `/opt/bin/opkg install ${packageName}`
    };
    
    const confirmModalText = document.getElementById("confirm-modal-text");
    confirmModalText.innerHTML = `Вы уверены, что хотите обновить OPKG пакет <strong>${packageName}</strong> до версии <strong>${version}</strong> через официальные списки пакетов?`;
    
    confirmModal.classList.add("active");
    pauseAutoRefresh();
}

// Modal Confirm Event Handlers
function handleConfirmCancel() {
    confirmModal.classList.remove("active");
    pendingUpdate = null;
    resumeAutoRefresh();
}

async function handleConfirmYes() {
    if (!pendingUpdate) return;
    
    confirmModal.classList.remove("active");
    const { service, version, url, isOpkg, command } = pendingUpdate;
    pendingUpdate = null;
    
    if (isOpkg) {
        logToConsole(service, `Запуск обновления OPKG пакета до версии ${version}...`, "cmd");
        logToConsole(service, `Выполнение команды: ${command}`, "output");
        
        try {
            const response = await fetch(`${routerHost}/api/exec`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ command }),
                mode: "cors"
            });
            
            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.success) {
                logToConsole(service, `Пакет успешно обновлен!\n${result.output}`, "success");
            } else {
                logToConsole(service, `Сбой обновления (код ${result.exit_code}):\n${result.output}`, "error");
            }
        } catch (e) {
            logToConsole(service, `Ошибка запроса на обновление: ${e.message}`, "error");
        } finally {
            resumeAutoRefresh();
            fetchRouterStatus(true);
        }
    } else {
        logToConsole(service, `Запуск обновления с GitHub до версии ${version}...`, "cmd");
        logToConsole(service, `Загрузка с: ${url}`, "output");
        
        // Temporarily disable buttons in that row
        const row = document.querySelector(`tr[data-service="${service}"]`);
        const upgradeBtns = row ? row.querySelectorAll(".btn-upgrade, .badge-update") : [];
        upgradeBtns.forEach(btn => btn.disabled = true);
        
        try {
            const response = await fetch(`${routerHost}/api/update`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ service, version, url }),
                mode: "cors"
            });
            
            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                logToConsole(service, `Обновление завершено успешно!`, "success");
                if (result.output) {
                    logToConsole(service, result.output, "output");
                }
            } else {
                logToConsole(service, `Сбой обновления: ${result.output}`, "error");
            }
            
        } catch (e) {
            logToConsole(service, `Сбой запроса на обновление: ${e.message}`, "error");
        } finally {
            resumeAutoRefresh();
            fetchRouterStatus(true);
        }
    }
}

// Execute Manual shell command
async function runManualCommand() {
    const command = cmdInput.value.trim();
    if (!command || !isConnected) return;
    
    cmdInput.value = "";
    logToConsole("Шелл", `Запуск команды: ${command}`, "cmd");
    btnRunCmd.disabled = true;
    
    try {
        const response = await fetch(`${routerHost}/api/exec`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ command }),
            mode: "cors"
        });
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        const result = await response.json();
        if (result.success) {
            logToConsole("Шелл", `Результат (код 0):\n${result.output}`, "success");
        } else {
            logToConsole("Шелл", `Сбой (код ${result.exit_code}):\n${result.output}`, "error");
        }
    } catch (e) {
        logToConsole("Шелл", `Ошибка запроса: ${e.message}`, "error");
    } finally {
        btnRunCmd.disabled = false;
    }
}

// Run OPKG list update
async function runOpkgUpdate() {
    if (!isConnected) return;
    
    logToConsole("OPKG", "Выполнение opkg update...", "cmd");
    btnOpkgUpdate.disabled = true;
    
    try {
        const response = await fetch(`${routerHost}/api/exec`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ command: "/opt/bin/opkg update" }),
            mode: "cors"
        });
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        const result = await response.json();
        if (result.success) {
            logToConsole("OPKG", `Списки пакетов успешно обновлены!\n${result.output}`, "success");
            // Reload status to fetch new versions in background
            fetchRouterStatus(true);
        } else {
            logToConsole("OPKG", `Сбой обновления списков (код ${result.exit_code}):\n${result.output}`, "error");
        }
    } catch (e) {
        logToConsole("OPKG", `Ошибка запроса к роутеру: ${e.message}`, "error");
    } finally {
        btnOpkgUpdate.disabled = false;
    }
}

function pauseAutoRefresh() {
    isRefreshPaused = true;
}

function resumeAutoRefresh() {
    isRefreshPaused = false;
}
