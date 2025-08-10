"""爬虫核心逻辑"""
import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional
from config import Config
from models import Token, TokenStore

try:
    from playwright.async_api import async_playwright
    import requests
except ImportError as e:
    print(f"缺少依赖包: {e}")
    print("请运行: uv sync 安装所有依赖")


class SparkScraper:
    """Spark代币监控爬虫"""
    
    def __init__(self, config: Config):
        self.config = config
        self.token_store = TokenStore()
        self.browser = None
        self.context = None
        self.page = None
        self.is_first_run = True
        self.initial_new_coin_data = None  # 移到这里初始化
    
    async def init_browser(self):
        """初始化浏览器（仅一次）"""
        if self.browser is None:
            print("🔧 初始化浏览器...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.config.browser_headless,
                args=['--no-sandbox'] if self.config.browser_headless else None
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            # 设置网络请求监听器
            async def handle_response(response):
                if self.config.api_url in response.url:
                    try:
                        # 获取请求的载荷
                        request = response.request
                        post_data = request.post_data
                        
                        # 检查是否是新币请求
                        if post_data and '"category":"new"' in post_data:
                            print(f"🔍 捕获到新币API请求")
                            data = await response.json()
                            api_data = data.get("data", [])
                            print(f"📈 新币数据：包含 {len(api_data)} 个代币")
                            
                            # 如果是初始化阶段，立即处理并显示前3个代币
                            if self.is_first_run and len(api_data) > 0:
                                print("📊 首次启动，显示最新3个代币...")
                                
                                # 解析所有代币
                                all_tokens = []
                                for item in api_data:
                                    try:
                                        token = Token.from_api_data(item)
                                        all_tokens.append(token)
                                        # 标记为已见过
                                        self.token_store.add_token(token)
                                    except Exception as e:
                                        print(f"处理代币数据失败: {e}")
                                        continue
                                
                                # 显示最新的3个
                                if all_tokens:
                                    sorted_tokens = sorted(all_tokens, key=lambda x: x.token_created_at, reverse=True)
                                    display_tokens = sorted_tokens[:3]
                                    print(f"\n🪙 当前最新的 {len(display_tokens)} 个代币:")
                                    self._print_token_list(display_tokens)
                                
                                # 切换到监听模式
                                self.is_first_run = False
                                print("✨ 初始化完成，切换到监听模式")
                            
                            # 如果是正常监听模式，检查新代币
                            elif not self.is_first_run:
                                self._process_and_display_tokens(api_data)
                        else:
                            # 忽略非新币请求，静默处理
                            pass
                            
                    except Exception as e:
                        print(f"解析API响应失败: {e}")
            
            self.page.on("response", handle_response)
            print("✅ 浏览器初始化完成")
    
    async def fetch_data_via_browser(self) -> Optional[List[dict]]:
        """通过浏览器访问页面获取数据"""
        try:
            await self.init_browser()
            
            print(f"正在访问页面: {self.config.monitor_url}")
            self.api_response_data = None
            
            # 访问页面
            await self.page.goto(self.config.monitor_url, wait_until="networkidle")
            
            # 等待API调用完成
            await asyncio.sleep(3)
            
            return self.api_response_data
                
        except Exception as e:
            print(f"浏览器获取数据失败: {e}")
            return None
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
    
    async def fetch_data_direct(self) -> Optional[List[dict]]:
        """直接调用API获取数据"""
        try:
            print(f"直接调用API: {self.config.api_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': self.config.monitor_url
            }
            
            response = requests.get(self.config.api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except Exception as e:
            print(f"API直接调用失败: {e}")
            return None
    
    def process_tokens(self, api_data: List[dict]) -> tuple[List[Token], List[Token]]:
        """处理代币数据，返回 (新代币列表, 所有代币列表)"""
        if not api_data:
            return [], []
        
        new_tokens = []
        all_tokens = []
        
        for item in api_data:
            try:
                token = Token.from_api_data(item)
                all_tokens.append(token)
                
                if self.is_first_run:
                    # 首次运行：显示过去30分钟内创建的代币
                    if token.is_newly_created(threshold_minutes=30):
                        new_tokens.append(token)
                    # 标记所有代币为已见过，避免下次重复显示
                    self.token_store.add_token(token)
                else:
                    # 正常运行：只显示新发现的代币
                    if self.token_store.is_new_token(token):
                        new_tokens.append(token)
                    
            except Exception as e:
                print(f"处理代币数据失败: {e}")
                continue
        
        return new_tokens, all_tokens
    
    def print_tokens(self, new_tokens: List[Token], all_tokens: List[Token]):
        """打印代币信息"""
        if self.is_first_run:
            if new_tokens:
                print(f"\n📈 过去30分钟内创建的代币 ({len(new_tokens)} 个):")
                self._print_token_list(new_tokens)
            else:
                # 首次启动没有新代币时，显示最新的几个代币信息
                print("过去30分钟内没有新创建的代币")
                if all_tokens:
                    print(f"\n🪙 当前所有代币信息 (显示最新 {min(3, len(all_tokens))} 个):")
                    # 按创建时间排序，显示最新的3个
                    sorted_tokens = sorted(all_tokens, key=lambda x: x.token_created_at, reverse=True)
                    self._print_token_list(sorted_tokens[:3])
        else:
            if new_tokens:
                print(f"\n🎉 发现 {len(new_tokens)} 个新代币:")
                self._print_token_list(new_tokens)
            else:
                print("没有发现新代币")
    
    def _print_token_list(self, tokens: List[Token]):
        """打印代币列表"""
        print("-" * 80)
        for token in tokens:
            print(f"代币名称: {token.name}")
            print(f"代币符号: {token.ticker}")
            print(f"合约地址: {token.token_address}")
            print(f"创建时间: {token.token_created_at}")
            if token.description:
                print(f"描述: {token.description}")
            print("-" * 80)
    
    def _process_and_display_tokens(self, api_data: list):
        """处理并显示代币数据"""
        new_tokens, all_tokens = self.process_tokens(api_data)
        
        if new_tokens:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 发现新代币!")
            self.print_tokens(new_tokens, all_tokens)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 收到新币API响应，暂无符合条件的新代币")
    
    async def run_once(self):
        """执行一次监控"""
        if self.is_first_run:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 首次启动，检查过去30分钟内的新代币...")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始检查新代币...")
        
        # 首先尝试浏览器方式
        api_data = await self.fetch_data_via_browser()
        
        # 如果浏览器方式失败，尝试直接API调用
        if api_data is None:
            print("浏览器方式失败，尝试直接API调用...")
            api_data = await self.fetch_data_direct()
        
        if api_data is None:
            print("所有获取数据方式都失败了")
            return
        
        # 处理代币数据
        new_tokens, all_tokens = self.process_tokens(api_data)
        
        # 打印结果
        self.print_tokens(new_tokens, all_tokens)
        
        # 标记首次运行完成
        if self.is_first_run:
            self.is_first_run = False
    
    async def run_continuous(self):
        """持续运行监控 - 监听模式"""
        print(f"🚀 Spark代币监控器启动!")
        print(f"📡 监控地址: {self.config.monitor_url}")
        print(f"🔍 浏览器模式: {'隐藏' if self.config.browser_headless else '可见'}")
        print("👂 监听模式：持续监听网页自动执行的API请求")
        print("=" * 80)
        
        try:
            # 初始化浏览器并保持打开状态
            await self.init_browser()
            
            # 首次访问页面获取初始数据
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 首次启动，等待网页加载...")
            try:
                await self.page.goto(self.config.monitor_url, wait_until="networkidle", timeout=60000)
                print("📡 页面加载完成，监听器已激活")
            except Exception as e:
                print(f"页面加载失败: {e}")
                self.is_first_run = False
            
            print(f"\n🔄 现在持续监听网页自动执行的API请求...")
            print("💡 网页会自动刷新并执行API请求，无需手动干预")
            print("⏹️  按 Ctrl+C 退出监控\n")
            
            # 设置API响应监听器处理新数据
            async def handle_response(response):
                if self.config.api_url in response.url:
                    try:
                        # 获取请求的载荷
                        request = response.request
                        post_data = request.post_data
                        
                        # 只处理新币请求
                        if post_data and '"category":"new"' in post_data:
                            print(f"🔍 捕获到新币API请求")
                            data = await response.json()
                            api_data = data.get("data", [])
                            print(f"📈 新币数据：包含 {len(api_data)} 个代币")
                            
                            # 处理数据并显示结果
                            self._process_and_display_tokens(api_data)
                        else:
                            # 忽略非新币请求，静默处理
                            pass
                            
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 解析API响应失败: {e}")
            
            # 重新绑定响应监听器
            self.page.on("response", handle_response)
            
            # 保持程序运行，持续监听
            while True:
                await asyncio.sleep(1)  # 保持事件循环运行
                    
        except KeyboardInterrupt:
            print("\n👋 用户中断，程序退出")
        except Exception as e:
            print(f"❌ 运行出错: {e}")
        finally:
            # 确保浏览器被正确关闭
            await self.close_browser()
            print("🔧 浏览器已关闭")


async def main():
    """主函数"""
    # 加载配置
    config = Config.from_env()
    
    # 创建爬虫实例
    scraper = SparkScraper(config)
    
    # 运行
    await scraper.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())
