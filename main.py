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
                        data = await response.json()
                        self.api_response_data = data.get("data", [])
                        print(f"捕获到API响应，包含 {len(self.api_response_data)} 个代币")
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
    
    def process_tokens(self, api_data: List[dict]) -> List[Token]:
        """处理代币数据"""
        if not api_data:
            return []
        
        new_tokens = []
        
        for item in api_data:
            try:
                token = Token.from_api_data(item)
                
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
        
        return new_tokens
    
    def print_new_tokens(self, tokens: List[Token]):
        """打印新代币信息"""
        if not tokens:
            if self.is_first_run:
                print("过去30分钟内没有新创建的代币")
            else:
                print("没有发现新代币")
            return
        
        if self.is_first_run:
            print(f"\n📈 过去30分钟内创建的代币 ({len(tokens)} 个):")
        else:
            print(f"\n🎉 发现 {len(tokens)} 个新代币:")
        print("-" * 80)
        
        for token in tokens:
            print(f"代币名称: {token.name}")
            print(f"代币符号: {token.ticker}")
            print(f"合约地址: {token.token_address}")
            print(f"创建时间: {token.token_created_at}")
            if token.description:
                print(f"描述: {token.description}")
            print("-" * 80)
    
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
        new_tokens = self.process_tokens(api_data)
        
        # 打印结果
        self.print_new_tokens(new_tokens)
        
        # 标记首次运行完成
        if self.is_first_run:
            self.is_first_run = False
    
    async def run_continuous(self):
        """持续运行监控"""
        print(f"🚀 Spark代币监控器启动!")
        print(f"📡 监控地址: {self.config.monitor_url}")
        print(f"⏰ 检查间隔: {self.config.check_interval_minutes} 分钟")
        print(f"🔍 浏览器模式: {'隐藏' if self.config.browser_headless else '可见'}")
        print("🔄 浏览器将保持打开状态，避免重复初始化")
        print("=" * 80)
        
        try:
            while True:
                try:
                    await self.run_once()
                    
                    # 等待下次检查
                    if self.is_first_run:  # 这个判断其实不会成立，因为run_once会设置为False
                        print(f"\n⏱️  首次检查完成，等待 {self.config.check_interval_minutes} 分钟后进行定时检查...\n")
                    else:
                        print(f"\n⏱️  等待 {self.config.check_interval_minutes} 分钟后进行下次检查...\n")
                    
                    await asyncio.sleep(self.config.check_interval_minutes * 60)
                    
                except KeyboardInterrupt:
                    print("\n👋 用户中断，程序退出")
                    break
                except Exception as e:
                    print(f"❌ 运行出错: {e}")
                    print("⏱️  5秒后重试...")
                    await asyncio.sleep(5)
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
