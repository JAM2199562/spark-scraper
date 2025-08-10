"""配置文件"""
import os
from dataclasses import dataclass
from typing import Optional

# 尝试加载python-dotenv来读取.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("警告: python-dotenv 未安装，将直接使用环境变量")

@dataclass
class Config:
    """应用配置类"""
    # 监控间隔时间（分钟）
    check_interval_minutes: int = 5
    
    # 监控的网页URL
    monitor_url: str = "https://regtest.luminex.pages.dev/spark/pulse"
    
    # API URL
    api_url: str = "https://brc20-api.luminex.io/regtest/spark/pulse"
    
    # 浏览器是否可见（调试用）
    browser_headless: bool = False
    
    # 时区偏移（小时）
    timezone_offset_hours: int = 8
    
    # Bark推送配置
    bark_endpoint: str = ""
    bark_push_on_startup: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            check_interval_minutes=int(os.getenv("CHECK_INTERVAL_MINUTES", "5")),
            monitor_url=os.getenv("MONITOR_URL", "https://regtest.luminex.pages.dev/spark/pulse"),
            api_url=os.getenv("API_URL", "https://brc20-api.luminex.io/regtest/spark/pulse"),
            browser_headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            timezone_offset_hours=int(os.getenv("TIMEZONE_OFFSET_HOURS", "8")),
            bark_endpoint=os.getenv("BARK_ENDPOINT", ""),
            bark_push_on_startup=os.getenv("BARK_PUSH_ON_STARTUP", "true").lower() == "true",
        )