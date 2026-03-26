"""
消息处理层

处理 SECS-II 消息的接收、解析和回复。
"""

from .base_handler import BaseMessageHandler, MessageHandlerRegistry
from .dispatcher import MessageDispatcher

__all__ = ["BaseMessageHandler", "MessageHandlerRegistry", "MessageDispatcher"]
