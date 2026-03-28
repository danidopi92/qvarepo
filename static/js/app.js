const THEME_STORAGE_KEY = "qvatelTheme";

function getPreferredTheme() {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
        return storedTheme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
    document.body.dataset.theme = theme;
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) {
        return;
    }

    const icon = toggle.querySelector("i");
    const label = toggle.querySelector("span");
    const isDark = theme === "dark";

    if (icon) {
        icon.className = isDark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    }
    if (label) {
        label.textContent = isDark ? "Modo claro" : "Modo oscuro";
    }

    const nextLabel = isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro";
    toggle.setAttribute("aria-label", nextLabel);
    toggle.setAttribute("title", nextLabel);
}

function initializeThemeToggle() {
    applyTheme(getPreferredTheme());

    const toggle = document.getElementById("theme-toggle");
    if (!toggle || toggle.dataset.bound === "true") {
        return;
    }

    toggle.dataset.bound = "true";
    toggle.addEventListener("click", function () {
        const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
        localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
        applyTheme(nextTheme);
    });
}

document.body.addEventListener("htmx:afterRequest", function () {
    const alerts = document.querySelectorAll(".alert");
    if (alerts.length) {
        setTimeout(() => alerts.forEach((alert) => alert.remove()), 3500);
    }
    applyCustomerColumnPreferences();
    initializeThemeToggle();
});

document.body.addEventListener("click", async function (event) {
    const trigger = event.target.closest(".js-copy-trigger");
    if (!trigger) {
        return;
    }

    const text = trigger.dataset.copyText;
    if (!text) {
        return;
    }

    try {
        await navigator.clipboard.writeText(text);
        const previous = trigger.textContent;
        trigger.textContent = "Copiado";
        setTimeout(() => {
            trigger.textContent = previous;
        }, 1600);
    } catch (_error) {
        const fallback = document.createElement("input");
        fallback.value = text;
        document.body.appendChild(fallback);
        fallback.select();
        document.execCommand("copy");
        fallback.remove();
        const previous = trigger.textContent;
        trigger.textContent = "Copiado";
        setTimeout(() => {
            trigger.textContent = previous;
        }, 1600);
    }
});

const CUSTOMER_COLUMNS_STORAGE_KEY = "qvatelCustomerColumns";

function getCustomerColumnsManager() {
    return document.getElementById("customer-columns-manager");
}

function getCustomerColumnItems() {
    const manager = getCustomerColumnsManager();
    return manager ? Array.from(manager.querySelectorAll(".customer-column-item")) : [];
}

function getDefaultCustomerColumns() {
    return getCustomerColumnItems().map((item) => ({
        key: item.dataset.columnKey,
        visible: true,
    }));
}

function readCustomerColumnPreferences() {
    try {
        const stored = localStorage.getItem(CUSTOMER_COLUMNS_STORAGE_KEY);
        if (!stored) {
            return getDefaultCustomerColumns();
        }
        const parsed = JSON.parse(stored);
        return Array.isArray(parsed) && parsed.length ? parsed : getDefaultCustomerColumns();
    } catch (_error) {
        return getDefaultCustomerColumns();
    }
}

function writeCustomerColumnPreferences(preferences) {
    localStorage.setItem(CUSTOMER_COLUMNS_STORAGE_KEY, JSON.stringify(preferences));
}

function syncCustomerColumnsManager() {
    const preferences = readCustomerColumnPreferences();
    const manager = getCustomerColumnsManager();
    if (!manager) {
        return;
    }
    const itemMap = new Map(getCustomerColumnItems().map((item) => [item.dataset.columnKey, item]));
    preferences.forEach((preference) => {
        const item = itemMap.get(preference.key);
        if (!item) {
            return;
        }
        manager.appendChild(item);
        const toggle = item.querySelector(".customer-column-toggle");
        if (toggle) {
            toggle.checked = preference.visible !== false;
        }
    });
}

function applyCustomerColumnPreferences() {
    const wrapper = document.querySelector("[data-column-configurable='true']");
    if (!wrapper) {
        return;
    }

    const preferences = readCustomerColumnPreferences();
    const preferenceMap = new Map(preferences.map((item) => [item.key, item]));
    const rows = wrapper.querySelectorAll("table tr");

    rows.forEach((row) => {
        const startCells = Array.from(row.querySelectorAll("[data-column-fixed='start']"));
        const endCells = Array.from(row.querySelectorAll("[data-column-fixed='end']"));
        const configurableCells = Array.from(row.querySelectorAll("[data-column-key]"));
        const configurableMap = new Map(configurableCells.map((cell) => [cell.dataset.columnKey, cell]));

        preferences.forEach((preference) => {
            const cell = configurableMap.get(preference.key);
            if (!cell) {
                return;
            }
            cell.style.display = preference.visible === false ? "none" : "";
        });

        startCells.forEach((cell) => row.appendChild(cell));
        preferences.forEach((preference) => {
            const cell = configurableMap.get(preference.key);
            if (cell) {
                row.appendChild(cell);
            }
        });
        endCells.forEach((cell) => row.appendChild(cell));
    });
}

document.addEventListener("DOMContentLoaded", function () {
    initializeThemeToggle();
    syncCustomerColumnsManager();
    applyCustomerColumnPreferences();

    const manager = getCustomerColumnsManager();
    if (!manager) {
        return;
    }

    manager.addEventListener("click", function (event) {
        const item = event.target.closest(".customer-column-item");
        if (!item) {
            return;
        }

        if (event.target.closest(".customer-column-up")) {
            const previous = item.previousElementSibling;
            if (previous) {
                item.parentElement.insertBefore(item, previous);
            }
        }

        if (event.target.closest(".customer-column-down")) {
            const next = item.nextElementSibling;
            if (next) {
                item.parentElement.insertBefore(next, item);
            }
        }
    });

    const saveButton = document.getElementById("customer-columns-save");
    if (saveButton) {
        saveButton.addEventListener("click", function () {
            const preferences = getCustomerColumnItems().map((item) => ({
                key: item.dataset.columnKey,
                visible: item.querySelector(".customer-column-toggle")?.checked ?? true,
            }));
            writeCustomerColumnPreferences(preferences);
            applyCustomerColumnPreferences();
        });
    }

    const resetButton = document.getElementById("customer-columns-reset");
    if (resetButton) {
        resetButton.addEventListener("click", function () {
            writeCustomerColumnPreferences(getDefaultCustomerColumns());
            syncCustomerColumnsManager();
            applyCustomerColumnPreferences();
        });
    }
});
