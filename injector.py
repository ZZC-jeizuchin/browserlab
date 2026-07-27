"""
injector.py
注入管理器：负责生成在页面加载前执行的综合脚本。
聚合 Storage 守卫脚本、Fingerprint 伪装脚本等。
"""

import json


class Injector:
    @staticmethod
    def build_storage_guard(allow_write: bool,
                            managed_cookies: dict[str, str],
                            managed_local_storage: dict[str, str]) -> str:
        """生成 Storage 守卫脚本（完全代理读写，确保管理值始终可见）"""
        mc_json = json.dumps(managed_cookies)
        mls_json = json.dumps(managed_local_storage)
        allow = "true" if allow_write else "false"

        return f"""
(function() {{
    'use strict';
    if (window.__bl_storage_guard_installed) return;
    window.__bl_storage_guard_installed = true;

    const MANAGED_COOKIES = {mc_json};
    const MANAGED_LOCAL_STORAGE = {mls_json};
    const ALLOW_WRITE = {allow};

    // 保存原始方法
    const origCookieDesc = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
    const originalSetItem = Storage.prototype.setItem;
    const originalGetItem = Storage.prototype.getItem;
    const originalRemoveItem = Storage.prototype.removeItem;
    const originalClear = Storage.prototype.clear;
    const originalKey = Storage.prototype.key;
    const originalGetLength = Object.getOwnPropertyDescriptor(Storage.prototype, 'length').get;

    // -------- 虚拟 LocalStorage --------
    function getFullLocalStorage() {{
        const base = {{}};
        for (let i = 0; i < originalGetLength.call(localStorage); i++) {{
            const k = originalKey.call(localStorage, i);
            base[k] = originalGetItem.call(localStorage, k);
        }}
        return Object.assign(base, MANAGED_LOCAL_STORAGE);
    }}

    function applyManagedLocalStorage() {{
        for (const [key, value] of Object.entries(MANAGED_LOCAL_STORAGE)) {{
            try {{ originalSetItem.call(localStorage, key, value); }} catch(e) {{}}
        }}
    }}

    applyManagedLocalStorage();

    Storage.prototype.setItem = function(key, value) {{
        if (this !== window.localStorage) return originalSetItem.apply(this, arguments);
        if (!ALLOW_WRITE && !(key in MANAGED_LOCAL_STORAGE)) {{
            console.warn('[BrowserLab] localStorage 写入被禁止');
            return;
        }}
        if (key in MANAGED_LOCAL_STORAGE) {{
            console.warn('[BrowserLab] 忽略对管理键 "' + key + '" 的写入');
            return;
        }}
        return originalSetItem.call(this, key, value);
    }};

    Storage.prototype.getItem = function(key) {{
        if (this !== window.localStorage) return originalGetItem.apply(this, arguments);
        if (key in MANAGED_LOCAL_STORAGE) return MANAGED_LOCAL_STORAGE[key];
        return originalGetItem.call(this, key);
    }};

    Storage.prototype.removeItem = function(key) {{
        if (this !== window.localStorage) return originalRemoveItem.apply(this, arguments);
        if (key in MANAGED_LOCAL_STORAGE) {{
            console.warn('[BrowserLab] 禁止删除管理键 "' + key + '"');
            return;
        }}
        return originalRemoveItem.call(this, key);
    }};

    Storage.prototype.clear = function() {{
        if (this !== window.localStorage) return originalClear.apply(this, arguments);
        const keys = Object.keys(localStorage);
        for (const k of keys) {{
            if (!(k in MANAGED_LOCAL_STORAGE)) {{
                originalRemoveItem.call(this, k);
            }}
        }}
    }};

    Storage.prototype.key = function(index) {{
        if (this !== window.localStorage) return originalKey.apply(this, arguments);
        const full = Object.keys(getFullLocalStorage());
        return full[index] || null;
    }};

    Object.defineProperty(Storage.prototype, 'length', {{
        get: function() {{
            if (this !== window.localStorage) return originalGetLength.call(this);
            return Object.keys(getFullLocalStorage()).length;
        }},
        configurable: true
    }});

    // -------- 虚拟 Cookie --------
    function parseCookies(cookieStr) {{
        const result = {{}};
        cookieStr.split(';').forEach(pair => {{
            const idx = pair.indexOf('=');
            if (idx > 0) {{
                const name = decodeURIComponent(pair.substring(0, idx).trim());
                const value = decodeURIComponent(pair.substring(idx + 1).trim());
                result[name] = value;
            }}
        }});
        return result;
    }}

    function buildCookieString(cookieObj) {{
        return Object.entries(cookieObj).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('; ');
    }}

    function applyManagedCookies() {{
        for (const [name, value] of Object.entries(MANAGED_COOKIES)) {{
            try {{
                origCookieDesc.set.call(document, name + '=' + encodeURIComponent(value) + ';path=/;SameSite=None;Secure');
            }} catch(e) {{}}
        }}
    }}

    applyManagedCookies();

    Object.defineProperty(document, 'cookie', {{
        set: function(val) {{
            if (!ALLOW_WRITE) {{
                console.warn('[BrowserLab] Cookie 写入被禁止');
                return;
            }}
            const parts = val.split(';')[0].split('=');
            const name = decodeURIComponent(parts[0]);
            if (name in MANAGED_COOKIES) {{
                console.warn('[BrowserLab] 忽略对管理 Cookie "' + name + '" 的写入');
                return;
            }}
            origCookieDesc.set.call(document, val);
        }},
        get: function() {{
            const baseCookies = parseCookies(origCookieDesc.get.call(document));
            const merged = Object.assign(baseCookies, MANAGED_COOKIES);
            return buildCookieString(merged);
        }},
        configurable: true
    }});

    // 定期刷新管理值
    setInterval(function() {{
        applyManagedLocalStorage();
        applyManagedCookies();
        if (!ALLOW_WRITE) {{
            const keys = Object.keys(localStorage);
            for (const k of keys) {{
                if (!(k in MANAGED_LOCAL_STORAGE)) {{
                    try {{ originalRemoveItem.call(localStorage, k); }} catch(e) {{}}
                }}
            }}
            const base = parseCookies(origCookieDesc.get.call(document));
            for (const name in base) {{
                if (!(name in MANAGED_COOKIES)) {{
                    try {{ origCookieDesc.set.call(document, name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/'); }} catch(e) {{}}
                }}
            }}
        }}
    }}, 500);

    console.log('[BrowserLab] Storage guard installed.');
}})();
"""

    @staticmethod
    def build_fingerprint_script(fingerprint_overrides: dict, special: dict) -> str:
        """生成 Fingerprint 伪装脚本，覆盖所有可定义属性"""
        lines = []

        for path, value in fingerprint_overrides.items():
            js_val = json.dumps(value)
            parts = path.split('.')
            if len(parts) == 2:
                obj, prop = parts[0], parts[1]
                lines.append(
                    f"try {{ Object.defineProperty({obj}, '{prop}', {{ get: () => {js_val}, configurable: true }}); }} catch(e) {{}}"
                )
            elif len(parts) == 3:
                obj_path = '.'.join(parts[:-1])
                prop = parts[-1]
                lines.append(
                    f"try {{ if ({obj_path}) Object.defineProperty({obj_path}, '{prop}', {{ get: () => {js_val}, configurable: true }}); }} catch(e) {{}}"
                )

        tz = special.get("timezone")
        if tz:
            lines.append(f"""
const OrigDTF = Intl.DateTimeFormat;
Intl.DateTimeFormat = function(loc, opts) {{
    opts = opts || {{}};
    opts.timeZone = "{tz}";
    return new OrigDTF(loc, opts);
}};""")

        battery = special.get("battery")
        if battery and any(v is not None for v in battery.values()):
            filtered_battery = {k: v for k, v in battery.items() if v is not None}
            lines.append(f"navigator.getBattery = () => Promise.resolve({json.dumps(filtered_battery)});")

        devices = special.get("mediaDevices")
        if devices is not None:
            lines.append(f"navigator.mediaDevices.enumerateDevices = () => Promise.resolve({json.dumps(devices)});")

        conn = special.get("connection")
        if conn and any(v is not None and v != "" for v in conn.values()):
            lines.append(f"""
if (navigator.connection) {{
    Object.defineProperties(navigator.connection, {{
        effectiveType: {{ get: () => {json.dumps(conn['effectiveType'])}, configurable: true }},
        rtt: {{ get: () => {conn['rtt']}, configurable: true }},
        downlink: {{ get: () => {conn['downlink']}, configurable: true }}
    }});
}}
""")

        plugins = special.get("plugins", [])
        mime_types = special.get("mimeTypes", [])
        if plugins or mime_types:
            lines.append(f"""
Object.defineProperty(navigator, 'plugins', {{
    get: () => {json.dumps(plugins)},
    configurable: true
}});
Object.defineProperty(navigator, 'mimeTypes', {{
    get: () => {json.dumps(mime_types)},
    configurable: true
}});
""")

        webgl = special.get("webgl")
        if webgl and (webgl.get("vendor") or webgl.get("renderer")):
            vendor = webgl.get("vendor", "")
            renderer = webgl.get("renderer", "")
            lines.append(f"""
if (typeof WebGLRenderingContext !== 'undefined') {{
    const origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {{
        if (p === 37445) return "{vendor}";
        if (p === 37446) return "{renderer}";
        return origGetParam.call(this, p);
    }};
}}
""")

        script_body = "\n".join(lines)
        return f"""
(function() {{
    'use strict';
    if (window.__bl_fingerprint_installed) return;
    window.__bl_fingerprint_installed = true;
    {script_body}
    console.log('[BrowserLab] Fingerprint script injected.');
}})();
"""

    @staticmethod
    def build_complete_script(allow_write: bool,
                              managed_cookies: dict[str, str],
                              managed_local_storage: dict[str, str],
                              fingerprint_overrides: dict,
                              special: dict) -> str:
        """生成完整的注入脚本：Storage 守卫 + Fingerprint 伪装"""
        storage_guard = Injector.build_storage_guard(allow_write, managed_cookies, managed_local_storage)
        fingerprint_script = Injector.build_fingerprint_script(fingerprint_overrides, special)
        return fingerprint_script + "\n" + storage_guard
