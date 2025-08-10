"""Bark消息推送模块"""
import asyncio
import aiohttp
from typing import List, Optional
from datetime import datetime
from models import Token

class BarkNotifier:
    """Bark消息推送器"""
    
    def __init__(self, endpoint: str, debug: bool = False):
        self.endpoint = endpoint.rstrip('/')
        self.debug = debug
        
    def is_enabled(self) -> bool:
        """检查Bark推送是否已配置"""
        return bool(self.endpoint)
    
    async def send_message(self, title: str, body: str) -> bool:
        """发送Bark推送消息"""
        if not self.is_enabled():
            if self.debug:
                print("⚠️ Bark端点未配置，跳过推送")
            return False
        
        try:
            # Bark API格式: GET {endpoint}/{title}/{body}
            # URL编码处理特殊字符
            import urllib.parse
            encoded_title = urllib.parse.quote(title, safe='')
            encoded_body = urllib.parse.quote(body, safe='')
            
            url = f"{self.endpoint}/{encoded_title}/{encoded_body}"
            
            if self.debug:
                print(f"📱 发送Bark推送: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        if self.debug:
                            print(f"✅ Bark推送成功: {result}")
                        return True
                    else:
                        print(f"❌ Bark推送失败，状态码: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            print("❌ Bark推送超时")
            return False
        except Exception as e:
            print(f"❌ Bark推送异常: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    async def send_startup_message(self, tokens: List[Token]) -> bool:
        """发送启动时的消息"""
        if not tokens:
            title = "🚀 Spark监控器启动"
            body = "监控器已启动，当前没有新代币"
        else:
            title = "🚀 Spark监控器启动"
            body = f"监控器已启动，当前最新的{len(tokens)}个代币:\\n"
            for i, token in enumerate(tokens, 1):
                body += f"{i}. {token.name} ({token.ticker})\\n"
        
        return await self.send_message(title, body)
    
    async def send_new_token_message(self, tokens: List[Token]) -> bool:
        """发送新代币发现的消息"""
        if not tokens:
            return False
        
        if len(tokens) == 1:
            token = tokens[0]
            title = "🎉 发现新代币"
            body = f"代币名称: {token.name}\\n"
            body += f"代币符号: {token.ticker}\\n"
            body += f"合约地址: {token.token_address}\\n"
            body += f"创建时间: {token.token_created_at}"
            if token.description:
                body += f"\\n描述: {token.description}"
        else:
            title = f"🎉 发现{len(tokens)}个新代币"
            body = ""
            for i, token in enumerate(tokens, 1):
                body += f"{i}. {token.name} ({token.ticker})\\n"
                if i >= 5:  # 最多显示5个，避免消息过长
                    body += f"...还有{len(tokens) - 5}个代币"
                    break
        
        return await self.send_message(title, body)