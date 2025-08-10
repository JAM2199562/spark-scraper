#!/usr/bin/env python3
"""演示版本 - 使用本地JSON数据模拟功能"""
import asyncio
import json
from datetime import datetime
from config import Config
from models import Token, TokenStore

class SparkScraperDemo:
    """Spark代币监控爬虫演示版"""
    
    def __init__(self, config: Config):
        self.config = config
        self.token_store = TokenStore()
    
    def load_demo_data(self) -> list:
        """加载演示数据"""
        try:
            with open('resp.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('data', [])
        except Exception as e:
            print(f"加载演示数据失败: {e}")
            return []
    
    def process_tokens(self, api_data: list) -> list:
        """处理代币数据"""
        if not api_data:
            return []
        
        new_tokens = []
        
        for item in api_data:
            try:
                token = Token.from_api_data(item)
                
                # 检查是否是新代币
                if self.token_store.is_new_token(token):
                    new_tokens.append(token)
                    
            except Exception as e:
                print(f"处理代币数据失败: {e}")
                continue
        
        return new_tokens
    
    def print_new_tokens(self, tokens: list):
        """打印新代币信息"""
        if not tokens:
            print("没有发现新代币")
            return
        
        print(f"\n🎉 发现 {len(tokens)} 个代币:")
        print("-" * 80)
        
        for token in tokens:
            print(f"代币名称: {token.name}")
            print(f"代币符号: {token.ticker}")
            print(f"合约地址: {token.token_address}")
            print(f"创建时间: {token.token_created_at}")
            if token.description:
                print(f"描述: {token.description}")
            print("-" * 80)
    
    async def run_demo(self):
        """运行演示"""
        print("🧪 Spark代币监控器 - 演示模式")
        print("📁 使用本地数据文件: resp.json")
        print("=" * 80)
        
        # 加载演示数据
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 加载演示数据...")
        api_data = self.load_demo_data()
        
        if not api_data:
            print("❌ 无法加载演示数据")
            return
        
        print(f"✅ 加载了 {len(api_data)} 个代币数据")
        
        # 模拟首次运行 - 所有代币都是新的
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 首次运行 - 所有代币都是新的...")
        new_tokens = self.process_tokens(api_data)
        self.print_new_tokens(new_tokens[:5])  # 只显示前5个
        
        if len(new_tokens) > 5:
            print(f"... 还有 {len(new_tokens) - 5} 个代币未显示\n")
        
        # 模拟第二次运行 - 没有新代币
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 模拟第二次检查...")
        await asyncio.sleep(2)
        new_tokens_2nd = self.process_tokens(api_data)
        self.print_new_tokens(new_tokens_2nd)
        
        print(f"\n✅ 演示完成!")
        print("💡 这展示了程序如何识别新代币并避免重复报告")

async def main():
    """主函数"""
    config = Config.from_env()
    scraper = SparkScraperDemo(config)
    await scraper.run_demo()

if __name__ == "__main__":
    asyncio.run(main())