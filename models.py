"""数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class Token:
    """代币信息"""
    token_id: int
    name: str
    ticker: str
    token_address: str
    token_created_at: str
    description: Optional[str] = None
    
    def __post_init__(self):
        """格式化创建时间"""
        if isinstance(self.token_created_at, str):
            try:
                # 解析ISO时间格式
                self.created_datetime = datetime.fromisoformat(
                    self.token_created_at.replace('Z', '+00:00')
                )
            except ValueError:
                self.created_datetime = None
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "Token":
        """从API数据创建Token对象"""
        token_data = data.get("token", {})
        return cls(
            token_id=token_data.get("id"),
            name=token_data.get("name"),
            ticker=token_data.get("ticker"),
            token_address=token_data.get("token_address"),
            token_created_at=token_data.get("token_created_at"),
            description=token_data.get("description")
        )
    
    def is_newly_created(self, threshold_minutes: int = 30) -> bool:
        """判断是否是新创建的代币（在threshold_minutes分钟内创建）"""
        if not self.created_datetime:
            return False
        
        now = datetime.now(self.created_datetime.tzinfo)
        time_diff = now - self.created_datetime
        return time_diff.total_seconds() < threshold_minutes * 60

@dataclass  
class TokenStore:
    """代币存储管理"""
    seen_tokens: set[int]
    
    def __init__(self):
        self.seen_tokens = set()
    
    def is_new_token(self, token: Token) -> bool:
        """检查是否是新代币"""
        if token.token_id in self.seen_tokens:
            return False
        
        self.seen_tokens.add(token.token_id)
        return True
    
    def add_token(self, token: Token):
        """添加代币到已知集合"""
        self.seen_tokens.add(token.token_id)