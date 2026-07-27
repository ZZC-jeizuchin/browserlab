"""
fingerprint.py
Fingerprint 抽象层：管理 JS 暴露属性的预设值，覆盖几乎所有可读属性。
"""


class Fingerprint:
    PRESETS = {
        "Android Tablet (XP34A)": {
            "navigator.userAgent": "Mozilla/5.0 (Linux; Android 15; XP34A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "navigator.appVersion": "5.0 (Linux; Android 15; XP34A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
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
            "navigator.plugins": [],
            "navigator.mimeTypes": [],
            "navigator.cookieEnabled": True,
            "navigator.onLine": True,
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
            "navigator.userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "navigator.appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
            "navigator.plugins": [],
            "navigator.mimeTypes": [],
            "navigator.cookieEnabled": True,
            "navigator.onLine": True,
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

    def __init__(self):
        self.properties = {
            "navigator.userAgent": "",
            "navigator.appVersion": "",
            "navigator.platform": "",
            "navigator.hardwareConcurrency": 0,
            "navigator.deviceMemory": 0,
            "navigator.maxTouchPoints": 0,
            "navigator.vendor": "",
            "navigator.vendorSub": "",
            "navigator.productSub": "",
            "navigator.doNotTrack": "",
            "navigator.language": "",
            "navigator.languages": [],
            "navigator.plugins": [],
            "navigator.mimeTypes": [],
            "navigator.cookieEnabled": None,
            "navigator.onLine": None,
            "screen.width": 0,
            "screen.height": 0,
            "screen.availWidth": 0,
            "screen.availHeight": 0,
            "screen.colorDepth": 0,
            "screen.pixelDepth": 0,
            "navigator.connection.effectiveType": "",
            "navigator.connection.rtt": 0,
            "navigator.connection.downlink": 0,
            "timezone": "",
            "battery.charging": None,
            "battery.level": None,
            "battery.chargingTime": None,
            "battery.dischargingTime": None,
            "mediaDevices": None,
            "webgl.vendor": "",
            "webgl.renderer": "",
        }

    def apply_preset(self, preset_name: str) -> bool:
        if preset_name in self.PRESETS:
            self.properties = dict(self.PRESETS[preset_name])
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

    def get_injection_overrides(self) -> dict:
        """返回可直接用 defineProperty 覆盖的简单属性"""
        special_keys = {
            "navigator.plugins", "navigator.mimeTypes",
            "timezone", "mediaDevices",
            "battery.charging", "battery.level", "battery.chargingTime", "battery.dischargingTime",
            "navigator.connection.effectiveType", "navigator.connection.rtt", "navigator.connection.downlink",
            "webgl.vendor", "webgl.renderer",
        }
        overrides = {}
        for key, val in self.properties.items():
            if key in special_keys:
                continue
            if val is None or val == "":
                continue
            overrides[key] = val
        return overrides

    def get_special_injection_data(self) -> dict:
        """返回需要特殊脚本处理的配置"""
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
            },
            "plugins": self.properties.get("navigator.plugins", []),
            "mimeTypes": self.properties.get("navigator.mimeTypes", []),
            "webgl": {
                "vendor": self.properties.get("webgl.vendor", ""),
                "renderer": self.properties.get("webgl.renderer", ""),
            }
        }
