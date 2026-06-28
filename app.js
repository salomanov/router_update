// State Management
let routerHost = "http://192.168.1.1:8089";
let isConnected = false;
let refreshIntervalId = null;
const REFRESH_RATE_MS = 6000; // Auto refresh every 6 seconds

// Service Meta Information
const SERVICE_METADATA = {
    "dropbear": { name: "SSH (Dropbear)", desc: "Сервер удаленного доступа SSH" },
    "nfqws2": { name: "nfqws2 (zapret)", desc: "Обход систем фильтрации DPI / zapret" },
    "tg-ws-proxy": { name: "tg-ws-proxy", desc: "Прокси Telegram MTProto WebSockets (Go)" },
    "mosquitto": { name: "Mosquitto MQTT", desc: "Брокер сообщений для умного дома" },
    "lighttpd": { name: "Lighttpd", desc: "Веб-сервер роутера" },
    "tuya-mqtt-calibrator": { name: "Tuya MQTT Calibrator", desc: "Калибратор Tuya датчиков" },
    "usque": { name: "Usque SOCKS5", desc: "SOCKS5 прокси-клиент" }
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
const servicesTbody = document.getElementById("services-tbody");
const consoleOutput = document.getElementById("console-output");
const btnClearConsole = document.getElementById("btn-clear-console");

// Modal Elements
const helpModal = document.getElementById("help-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnModalOk = document.getElementById("btn-modal-ok");

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
    btnClearConsole.addEventListener("click", clearConsole);
    
    // Modal events
    btnCloseModal.addEventListener("click", toggleModal);
    btnModalOk.addEventListener("click", toggleModal);
    
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
            refreshIntervalId = setInterval(() => fetchRouterStatus(true), REFRESH_RATE_MS);
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
        
        if (!isRefresh) {
            logToConsole("Система", "Успешно подключено к роутеру!", "success");
            setConnectionState("online");
        }
        
        renderSystemStats(data.system);
        renderServicesTable(data.services, data.versions);
        
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
function renderServicesTable(services, versions) {
    if (!services) return;
    
    servicesTbody.innerHTML = "";
    
    for (const key in SERVICE_METADATA) {
        const meta = SERVICE_METADATA[key];
        const status = services[key] || "unknown";
        const installedVersion = versions ? versions[key] : null;
        
        const tr = document.createElement("tr");
        tr.setAttribute("data-service", key);
        
        // Name Column
        const tdName = document.createElement("td");
        tdName.className = "service-name";
        tdName.innerHTML = `<strong>${meta.name}</strong><span class="service-desc">${meta.desc}</span>`;
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
        
        // GitHub Release Column
        const tdGitHub = document.createElement("td");
        tdGitHub.className = "version-cell";
        
        const upstream = upstreamReleases[key];
        if (upstream) {
            if (upstream.error) {
                tdGitHub.innerHTML = `<span class="text-muted" title="${upstream.error}"><i class="fa-solid fa-triangle-exclamation"></i> Ошибка</span>`;
            } else if (upstream.latest) {
                const hasUpdate = isUpdateAvailable(installedVersion, upstream.latest);
                if (hasUpdate) {
                    tdGitHub.innerHTML = `${upstream.latest} <span class="badge-update warning" onclick="triggerUpdate('${key}', '${upstream.latest}', '${upstream.url}')" title="Нажмите, чтобы обновить"><i class="fa-solid fa-cloud-arrow-down"></i> Обновить!</span>`;
                } else {
                    tdGitHub.innerHTML = `${upstream.latest} <span class="badge-update success"><i class="fa-solid fa-check"></i> Актуально</span>`;
                }
            } else {
                tdGitHub.innerHTML = `<span class="badge-update loading"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка...</span>`;
            }
        } else {
            tdGitHub.innerHTML = `<span class="text-muted">—</span>`;
        }
        tr.appendChild(tdGitHub);
        
        // Actions Column
        const tdActions = document.createElement("td");
        tdActions.className = "actions-cell";
        
        if (status === "running") {
            tdActions.innerHTML = `
                <button class="btn-action stop" onclick="controlService('${key}', 'stop')" title="Остановить"><i class="fa-solid fa-stop"></i></button>
                <button class="btn-action restart" onclick="controlService('${key}', 'restart')" title="Перезапустить"><i class="fa-solid fa-arrow-rotate-right"></i></button>
            `;
        } else if (status === "stopped") {
            tdActions.innerHTML = `
                <button class="btn-action start" onclick="controlService('${key}', 'start')" title="Запустить"><i class="fa-solid fa-play"></i></button>
            `;
        } else {
            tdActions.innerHTML = `
                <button class="btn-action start" onclick="controlService('${key}', 'start')" title="Запустить"><i class="fa-solid fa-play"></i></button>
                <button class="btn-action stop" onclick="controlService('${key}', 'stop')" title="Остановить"><i class="fa-solid fa-stop"></i></button>
            `;
        }
        
        // Add Upgrade button directly in action column if update is available
        if (upstream && upstream.latest && isUpdateAvailable(installedVersion, upstream.latest) && upstream.url) {
            const updateBtn = document.createElement("button");
            updateBtn.className = "btn-upgrade";
            updateBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> Обновить до ${upstream.latest}`;
            updateBtn.onclick = () => triggerUpdate(key, upstream.latest, upstream.url);
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

// Trigger Service Update
async function triggerUpdate(service, version, url) {
    if (!isConnected) return;
    
    const confirmMsg = `Вы уверены, что хотите обновить ${service} до версии ${version}?`;
    if (!confirm(confirmMsg)) return;
    
    logToConsole(service, `Запуск обновления до версии ${version}...`, "cmd");
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
        
        // Immediately refresh status to reload versions
        fetchRouterStatus(true);
        
    } catch (e) {
        logToConsole(service, `Сбой запроса на обновление: ${e.message}`, "error");
    }
}
