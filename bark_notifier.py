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
        """发送Bark推送消息

        优先使用 POST JSON，避免URL长度限制导致的截断；当 POST 失败时回退到 GET。
        """
        if not self.is_enabled():
            if self.debug:
                print("⚠️ Bark端点未配置，跳过推送")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                # 先尝试 POST JSON 到 {endpoint}
                try:
                    if self.debug:
                        print(f"📱 发送Bark推送(POST): {self.endpoint}")
                        preview = body if len(body) <= 100 else body[:100] + "..."
                        print(f"📝 标题: {title} | 内容预览: {preview}")
                    payload = {"title": title, "body": body}
                    async with session.post(self.endpoint, json=payload, timeout=10) as response:
                        if response.status == 200:
                            result = await response.json()
                            if self.debug:
                                print(f"✅ Bark推送成功(POST): {result}")
                            return True
                        else:
                            if self.debug:
                                print(f"⚠️ POST失败，状态码: {response.status}，尝试GET回退")
                except asyncio.TimeoutError:
                    print("❌ Bark推送超时(POST)")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ POST异常，尝试GET回退: {e}")

                # GET 回退: {endpoint}/{title}/{body}
                import urllib.parse
                encoded_title = urllib.parse.quote(title, safe='')
                encoded_body = urllib.parse.quote(body, safe='')
                url = f"{self.endpoint}/{encoded_title}/{encoded_body}"
                if self.debug:
                    print(f"📱 发送Bark推送(GET回退): {url}")
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        if self.debug:
                            print(f"✅ Bark推送成功(GET): {result}")
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
            body = f"监控器已启动，当前最新的{len(tokens)}个代币:\n"
            for i, token in enumerate(tokens, 1):
                body += f"{i}. {token.name} ({token.ticker})\n"
        
        return await self.send_message(title, body)
    
    async def send_new_token_message(self, tokens: List[Token]) -> bool:
        """发送新代币发现的消息：每个代币单独一条消息"""
        if not tokens:
            return False

        any_success = False
        for token in tokens:
            title = "🎉 发现新代币"
            body_lines = [
                f"代币名称: {token.name}",
                f"代币符号: {token.ticker}",
                f"合约地址: {token.token_address}",
                f"创建时间: {token.token_created_at}",
            ]
            if token.description:
                body_lines.append(f"描述: {token.description}")
            body = "\n".join(body_lines)

            sent = await self.send_message(title, body)
            any_success = any_success or sent

        return any_success