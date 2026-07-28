"""
fingerprint.py
Fingerprint 抽象层：包含完整的分类属性列表、预设模板，以及特殊注入标志。
"""

class Fingerprint:
    # 预设模板（仅包含常用属性，完整列表可在管理界面按需修改）
    PRESETS = {
        "Android Tablet (XP34A)": {
            # 基础标识
            "navigator.platform": "Linux aarch64",
            "navigator.hardwareConcurrency": 8,
            "navigator.deviceMemory": 4,
            "navigator.maxTouchPoints": 10,
            "navigator.vendor": "Google Inc.",
            "navigator.vendorSub": "",
            "navigator.productSub": "20030107",
            "navigator.doNotTrack": "1",
            "navigator.language": "zh-CN",
            "navigator.languages": ["zh-CN", "zh", "en"],
            "screen.width": 1920,
            "screen.height": 1200,
            "screen.availWidth": 1920,
            "screen.availHeight": 1120,
            "screen.colorDepth": 24,
            "screen.pixelDepth": 24,
            "navigator.connection.effectiveType": "4g",
            "navigator.connection.rtt": 50,
            "navigator.connection.downlink": 10,
            "timezone": "Asia/Shanghai",
            "battery.charging": True,
            "battery.level": 0.85,
            "battery.chargingTime": 0,
            "battery.dischargingTime": None,
            "mediaDevices": [],
            "webgl.vendor": "Google Inc. (Qualcomm)",
            "webgl.renderer": "Adreno (TM) 650",
        },
        "Desktop Chrome (Windows)": {
            "navigator.platform": "Win32",
            "navigator.hardwareConcurrency": 16,
            "navigator.deviceMemory": 8,
            "navigator.maxTouchPoints": 0,
            "navigator.vendor": "Google Inc.",
            "navigator.vendorSub": "",
            "navigator.productSub": "20030107",
            "navigator.doNotTrack": None,
            "navigator.language": "en-US",
            "navigator.languages": ["en-US", "en"],
            "screen.width": 1920,
            "screen.height": 1080,
            "screen.availWidth": 1920,
            "screen.availHeight": 1040,
            "screen.colorDepth": 24,
            "screen.pixelDepth": 24,
            "navigator.connection.effectiveType": "4g",
            "navigator.connection.rtt": 100,
            "navigator.connection.downlink": 5,
            "timezone": "America/New_York",
            "battery.charging": True,
            "battery.level": 0.95,
            "battery.chargingTime": 0,
            "battery.dischargingTime": None,
            "mediaDevices": [],
            "webgl.vendor": "Google Inc. (NVIDIA)",
            "webgl.renderer": "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        },
    }

    # 分类属性定义 (key: 属性路径, description: 中文说明, default: 默认值, special: 是否需要特殊注入脚本)
    CATEGORIES = {
        "1. 用户代理与平台": [
            ("navigator.platform", "操作系统平台", ""),
            ("navigator.vendor", "浏览器厂商", ""),
            ("navigator.vendorSub", "浏览器厂商补充", ""),
            ("navigator.productSub", "产品子版本", ""),
            ("navigator.appName", "应用名称", ""),
            ("navigator.appCodeName", "应用代码名", ""),
            ("navigator.appVersion", "应用版本", ""),
            ("navigator.oscpu", "OS/CPU (Firefox)", "", True),  # 需要特殊处理
            ("navigator.buildID", "构建ID (Firefox)", "", True),
            ("navigator.webdriver", "自动化标志", "", True),  # 通常设为 false
            ("navigator.userAgent", "UA 字符串 (注意：与请求头独立)", "", True),
        ],
        "2. 屏幕与显示": [
            ("screen.width", "屏幕宽度", 0),
            ("screen.height", "屏幕高度", 0),
            ("screen.availWidth", "可用屏幕宽度", 0),
            ("screen.availHeight", "可用屏幕高度", 0),
            ("screen.colorDepth", "颜色深度", 0),
            ("screen.pixelDepth", "像素深度", 0),
            ("devicePixelRatio", "设备像素比", 0),
            ("innerWidth", "视口宽度", 0),
            ("innerHeight", "视口高度", 0),
            ("screen.orientation.type", "屏幕方向", "", True),
            ("screen.orientation.angle", "屏幕旋转角度", 0, True),
        ],
        "3. 电池与网络": [
            ("battery.charging", "是否充电", True, True),
            ("battery.level", "电量 (0-1)", 0.0, True),
            ("battery.chargingTime", "充电时间", 0, True),
            ("battery.dischargingTime", "放电时间", None, True),
            ("navigator.connection.effectiveType", "网络类型 (4g/3g)", "", True),
            ("navigator.connection.rtt", "RTT (ms)", 0, True),
            ("navigator.connection.downlink", "下行带宽 (Mbps)", 0, True),
            ("navigator.connection.saveData", "省流量模式", False, True),
        ],
        "4. 硬件与内存": [
            ("navigator.hardwareConcurrency", "CPU 核心数", 0),
            ("navigator.deviceMemory", "设备内存 (GB)", 0),
            ("navigator.maxTouchPoints", "最大触控点数", 0),
        ],
        "5. 图形与 GPU": [
            ("webgl.vendor", "WebGL 厂商 (UNMASKED_VENDOR_WEBGL)", "", True),
            ("webgl.renderer", "WebGL 渲染器 (UNMASKED_RENDERER_WEBGL)", "", True),
            ("webgl.MAX_TEXTURE_SIZE", "最大纹理尺寸", 0, True),
            ("webgl.MAX_RENDERBUFFER_SIZE", "最大渲染缓冲大小", 0, True),
            ("webgl.MAX_VIEWPORT_DIMS", "最大视口尺寸", [0,0], True),
            ("webgl.MAX_VERTEX_ATTRIBS", "最大顶点属性", 0, True),
            ("webgl.MAX_TEXTURE_IMAGE_UNITS", "纹理单元数", 0, True),
            ("webgl2.supported", "WebGL2 支持", False, True),
            # WebGL 扩展列表较长，可用特殊脚本处理
        ],
        "6. 音频指纹": [
            ("audio.sampleRate", "采样率", 44100, True),
            ("audio.state", "状态 (running/suspended)", "", True),
            # 完整的音频指纹通常需要固定 AudioBuffer 渲染结果，需特殊脚本
        ],
        "7. 字体检测": [
            ("fonts.installed", "已安装字体列表 (空数组表示隐藏)", [], True),
            # 字体指纹复杂，通常通过伪造 document.fonts 实现
        ],
        "8. 插件与 MIME": [
            ("navigator.plugins", "插件列表", [], True),
            ("navigator.mimeTypes", "MIME 类型列表", [], True),
        ],
        "9. 国际化 (Intl)": [
            ("navigator.language", "浏览器语言", ""),
            ("navigator.languages", "用户语言偏好列表", []),
            ("timezone", "时区 (如 Asia/Shanghai)", "", True),
            # Intl API 的其他属性可以通过重写 DateTimeFormat 等实现（已在 injector 中处理）
        ],
        "10. 传感器与设备": [
            ("sensors.accelerometer", "加速度计", False, True),
            ("sensors.gyroscope", "陀螺仪", False, True),
            ("sensors.magnetometer", "磁力计", False, True),
            ("sensors.ambientLight", "环境光传感器", False, True),
            ("sensors.proximity", "距离传感器", False, True),
            ("mediaDevices", "媒体设备列表 (空数组表示无摄像头/麦克风)", [], True),
        ],
        "11. 外设与连接": [
            ("navigator.bluetooth", "蓝牙", False, True),
            ("navigator.usb", "USB", False, True),
            ("navigator.serial", "串口", False, True),
            ("navigator.hid", "HID", False, True),
            ("nfc.supported", "NFC (NDEFReader)", False, True),
            ("midi.supported", "MIDI", False, True),
        ],
        "12. 存储与缓存": [
            ("storage.localStorage", "LocalStorage 是否存在", True, True),
            ("storage.sessionStorage", "SessionStorage 是否存在", True, True),
            ("storage.indexedDB", "IndexedDB 是否存在", True, True),
            ("storage.cacheStorage", "CacheStorage 是否存在", True, True),
            ("storage.opfs", "OPFS (Origin Private File System)", False, True),
            ("navigator.cookieEnabled", "Cookie 启用", True),
        ],
        "13. 性能与内存": [
            ("performance.memory.jsHeapSizeLimit", "JS 堆大小限制", 0, True),
            ("performance.memory.totalJSHeapSize", "总堆大小", 0, True),
            ("performance.memory.usedJSHeapSize", "已用堆大小", 0, True),
        ],
        "14. 自动化检测": [
            ("navigator.webdriver", "WebDriver 标志", False, True),
            ("window.chrome", "chrome 对象 (用于检测)", True, True),
            # 更多检测可通过特殊脚本伪造
        ],
        "15. 其他 Navigator 属性": [
            ("navigator.onLine", "在线状态", True),
            ("navigator.doNotTrack", "DNT", ""),
            ("navigator.javaEnabled", "Java 启用", False, True),
            ("navigator.pdfViewerEnabled", "PDF 查看器启用", True, True),
            ("navigator.virtualKeyboard", "虚拟键盘 API", False, True),
        ],
        "16. 窗口与文档环境": [
            ("outerWidth", "窗口外部宽度", 0),
            ("outerHeight", "窗口外部高度", 0),
            ("screenX", "窗口 X", 0),
            ("screenY", "窗口 Y", 0),
            ("scrollX", "滚动 X", 0),
            ("scrollY", "滚动 Y", 0),
            ("visualViewport.width", "可视视口宽度", 0, True),
            ("crossOriginIsolated", "跨域隔离", False, True),
            ("isSecureContext", "安全上下文", True, True),
            ("document.hidden", "文档隐藏", False, True),
            ("document.visibilityState", "可见性状态", "visible", True),
        ],
        "17. WebRTC (IP 泄漏)": [
            ("webrtc.privateIP", "本地 IP (可通过特殊脚本伪造)", "", True),
            # WebRTC IP 伪造需要重写 RTCPeerConnection，较为复杂
        ],
        "18. Canvas 指纹 (2D)": [
            ("canvas.noise", "是否添加噪点 (true/false)", False, True),
            # Canvas 指纹通常通过随机化 toDataURL 等实现，不是简单值覆盖
        ],
        "19. Audio 指纹 (完整)": [
            ("audio.noise", "是否添加噪声 (true/false)", False, True),
        ],
        "20. WebAssembly": [
            ("wasm.supported", "WebAssembly 支持", True, True),
            ("wasm.simd", "SIMD", True, True),
            ("wasm.threads", "Threads", True, True),
        ],
        "21. 共享内存": [
            ("crossOriginIsolated", "跨域隔离 (影响 SharedArrayBuffer)", False, True),
        ],
        "22. 媒体能力": [
            ("mediaCapabilities.h264", "H.264 支持", True, True),
            ("mediaCapabilities.h265", "H.265/HEVC", False, True),
            ("mediaCapabilities.vp8", "VP8", True, True),
            ("mediaCapabilities.vp9", "VP9", True, True),
            ("mediaCapabilities.av1", "AV1", False, True),
        ],
    }

    def __init__(self):
        # 仍然使用扁平字典存储当前值，从分类定义中初始化默认值
        self.properties = {}
        for category, props in self.CATEGORIES.items():
            for key, desc, default, *special in props:
                self.properties[key] = default
        # 兼容旧的属性（可能未在分类中列出）
        self.properties.update({
            "navigator.plugins": [],
            "navigator.mimeTypes": [],
            "timezone": "",
            "mediaDevices": None,
            "webgl.vendor": "",
            "webgl.renderer": "",
        })

    def apply_preset(self, preset_name: str) -> bool:
        if preset_name in self.PRESETS:
            for key, val in self.PRESETS[preset_name].items():
                if key in self.properties:
                    self.properties[key] = val
            return True
        return False

    def set_property(self, key: str, value):
        self.properties[key] = value

    def get_property(self, key: str):
        return self.properties.get(key)

    def get_all_properties(self) -> dict:
        return dict(self.properties)

    def add_custom_property(self, key: str, default_value=None):
        if key not in self.properties:
            self.properties[key] = default_value

    def get_categorized_properties(self) -> dict:
        """返回按类别组织的属性列表，供界面使用"""
        result = {}
        for category, props in self.CATEGORIES.items():
            result[category] = []
            for key, desc, default, *special in props:
                result[category].append({
                    "key": key,
                    "description": desc,
                    "value": self.properties.get(key, default),
                    "special": bool(special) if special else False
                })
        return result

    def get_injection_overrides(self) -> dict:
        """返回可直接用 defineProperty 覆盖的简单属性（不包含特殊属性）"""
        simple_props = {}
        # 特殊属性集
        special_keys = set()
        for category, props in self.CATEGORIES.items():
            for key, desc, default, *special in props:
                if special and special[0]:
                    special_keys.add(key)
        # 添加已知的特殊属性
        special_keys.update({
            "navigator.plugins", "navigator.mimeTypes",
            "timezone", "mediaDevices",
            "battery.charging", "battery.level", "battery.chargingTime", "battery.dischargingTime",
            "navigator.connection.effectiveType", "navigator.connection.rtt", "navigator.connection.downlink",
            "webgl.vendor", "webgl.renderer",
            "webgl.MAX_TEXTURE_SIZE", "webgl.MAX_RENDERBUFFER_SIZE", "webgl.MAX_VIEWPORT_DIMS",
            "webgl.MAX_VERTEX_ATTRIBS", "webgl.MAX_TEXTURE_IMAGE_UNITS",
            "audio.sampleRate", "audio.state",
            "fonts.installed",
            "sensors.accelerometer", "sensors.gyroscope", "sensors.magnetometer",
            "sensors.ambientLight", "sensors.proximity",
            "navigator.bluetooth", "navigator.usb", "navigator.serial", "navigator.hid",
            "nfc.supported", "midi.supported",
            "storage.localStorage", "storage.sessionStorage", "storage.indexedDB", "storage.cacheStorage", "storage.opfs",
            "performance.memory.jsHeapSizeLimit", "performance.memory.totalJSHeapSize", "performance.memory.usedJSHeapSize",
            "navigator.webdriver", "window.chrome",
            "navigator.javaEnabled", "navigator.pdfViewerEnabled", "navigator.virtualKeyboard",
            "visualViewport.width", "crossOriginIsolated", "isSecureContext",
            "document.hidden", "document.visibilityState",
            "webrtc.privateIP",
            "canvas.noise", "audio.noise",
            "wasm.supported", "wasm.simd", "wasm.threads",
            "mediaCapabilities.h264", "mediaCapabilities.h265", "mediaCapabilities.vp8", "mediaCapabilities.vp9", "mediaCapabilities.av1",
            "navigator.oscpu", "navigator.buildID", "navigator.userAgent",
            "screen.orientation.type", "screen.orientation.angle",
            "navigator.connection.saveData",
            "devicePixelRatio", "innerWidth", "innerHeight",
        })
        for key, val in self.properties.items():
            if key not in special_keys and val not in (None, ""):
                simple_props[key] = val
        return simple_props

    def get_special_injection_data(self) -> dict:
        """返回需要特殊脚本处理的配置（与 injector 协作）"""
        return {
            "timezone": self.properties.get("timezone", ""),
            "battery": {
                "charging": self.properties.get("battery.charging"),
                "level": self.properties.get("battery.level"),
                "chargingTime": self.properties.get("battery.chargingTime"),
                "dischargingTime": self.properties.get("battery.dischargingTime"),
            },
            "mediaDevices": self.properties.get("mediaDevices"),
            "connection": {
                "effectiveType": self.properties.get("navigator.connection.effectiveType", ""),
                "rtt": self.properties.get("navigator.connection.rtt", 0),
                "downlink": self.properties.get("navigator.connection.downlink", 0),
                "saveData": self.properties.get("navigator.connection.saveData", False),
            },
            "plugins": self.properties.get("navigator.plugins", []),
            "mimeTypes": self.properties.get("navigator.mimeTypes", []),
            "webgl": {
                "vendor": self.properties.get("webgl.vendor", ""),
                "renderer": self.properties.get("webgl.renderer", ""),
                "params": {
                    "MAX_TEXTURE_SIZE": self.properties.get("webgl.MAX_TEXTURE_SIZE", 0),
                    "MAX_RENDERBUFFER_SIZE": self.properties.get("webgl.MAX_RENDERBUFFER_SIZE", 0),
                    "MAX_VIEWPORT_DIMS": self.properties.get("webgl.MAX_VIEWPORT_DIMS", [0,0]),
                    "MAX_VERTEX_ATTRIBS": self.properties.get("webgl.MAX_VERTEX_ATTRIBS", 0),
                    "MAX_TEXTURE_IMAGE_UNITS": self.properties.get("webgl.MAX_TEXTURE_IMAGE_UNITS", 0),
                }
            },
            "audio": {
                "sampleRate": self.properties.get("audio.sampleRate", 44100),
                "noise": self.properties.get("audio.noise", False),
            },
            "canvas": {
                "noise": self.properties.get("canvas.noise", False),
            },
            "fonts": self.properties.get("fonts.installed", []),
            "sensors": {
                "accelerometer": self.properties.get("sensors.accelerometer", False),
                "gyroscope": self.properties.get("sensors.gyroscope", False),
                "magnetometer": self.properties.get("sensors.magnetometer", False),
                "ambientLight": self.properties.get("sensors.ambientLight", False),
                "proximity": self.properties.get("sensors.proximity", False),
            },
            "peripherals": {
                "bluetooth": self.properties.get("navigator.bluetooth", False),
                "usb": self.properties.get("navigator.usb", False),
                "serial": self.properties.get("navigator.serial", False),
                "hid": self.properties.get("navigator.hid", False),
                "nfc": self.properties.get("nfc.supported", False),
                "midi": self.properties.get("midi.supported", False),
            },
            "storage_features": {
                "localStorage": self.properties.get("storage.localStorage", True),
                "sessionStorage": self.properties.get("storage.sessionStorage", True),
                "indexedDB": self.properties.get("storage.indexedDB", True),
                "cacheStorage": self.properties.get("storage.cacheStorage", True),
                "opfs": self.properties.get("storage.opfs", False),
            },
            "wasm": {
                "supported": self.properties.get("wasm.supported", True),
                "simd": self.properties.get("wasm.simd", True),
                "threads": self.properties.get("wasm.threads", True),
            },
            "media_capabilities": {
                "h264": self.properties.get("mediaCapabilities.h264", True),
                "h265": self.properties.get("mediaCapabilities.h265", False),
                "vp8": self.properties.get("mediaCapabilities.vp8", True),
                "vp9": self.properties.get("mediaCapabilities.vp9", True),
                "av1": self.properties.get("mediaCapabilities.av1", False),
            },
            "webrtc": {
                "privateIP": self.properties.get("webrtc.privateIP", ""),
            },
            "performance_memory": {
                "jsHeapSizeLimit": self.properties.get("performance.memory.jsHeapSizeLimit", 0),
                "totalJSHeapSize": self.properties.get("performance.memory.totalJSHeapSize", 0),
                "usedJSHeapSize": self.properties.get("performance.memory.usedJSHeapSize", 0),
            },
            "webdriver_flag": self.properties.get("navigator.webdriver", False),
            "window_chrome": self.properties.get("window.chrome", True),
            # 其他自定义属性可以在这里扩展
        }
