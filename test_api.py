#!/usr/bin/env python3
"""简单测试脚本 - 仅测试API调用功能"""
import asyncio
import requests
from datetime import datetime

async def test_api_call():
    """测试直接API调用"""
    api_url = "https://brc20-api.luminex.io/regtest/spark/pulse"
    
    print(f"测试API调用: {api_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        tokens = data.get("data", [])
        
        print(f"✅ API调用成功，获取到 {len(tokens)} 个代币")
        
        if tokens:
            print("\n前3个代币信息:")
            for i, item in enumerate(tokens[:3]):
                token_data = item.get("token", {})
                print(f"\n{i+1}. 代币名称: {token_data.get('name')}")
                print(f"   代币符号: {token_data.get('ticker')}")  
                print(f"   合约地址: {token_data.get('token_address')}")
                print(f"   创建时间: {token_data.get('token_created_at')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        return False

async def main():
    print("🧪 开始测试 Spark 代币监控API...")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    success = await test_api_call()
    
    print("\n" + "-" * 60)
    if success:
        print("✅ 测试成功! API调用正常工作")
        print("\n接下来可以运行完整程序:")
        print("uv run python main.py")
    else:
        print("❌ 测试失败! 请检查网络连接")

if __name__ == "__main__":
    asyncio.run(main())