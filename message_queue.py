import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from loguru import logger
from enum import Enum


class MessageType(Enum):
    """消息类型枚举"""
    CHAT = "chat"
    SYSTEM = "system"
    HEARTBEAT = "heartbeat"
    TYPING = "typing"
    ORDER = "order"
    UNKNOWN = "unknown"


class MessagePriority(Enum):
    """消息优先级枚举"""
    HIGH = 1    # 高优先级（订单消息、系统消息）
    NORMAL = 2  # 普通优先级（聊天消息）
    LOW = 3     # 低优先级（心跳、输入状态）


@dataclass
class QueuedMessage:
    """队列中的消息对象"""
    id: str
    message_type: MessageType
    priority: MessagePriority
    raw_data: Dict[str, Any]
    websocket: Any
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class MessageQueue:
    """异步消息队列管理器"""
    
    def __init__(self, max_queue_size: int = 1000, max_workers: int = 5):
        self.max_queue_size = max_queue_size
        self.max_workers = max_workers
        
        # 使用优先级队列
        self.queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        
        # 消息处理器字典
        self.handlers: Dict[MessageType, Callable] = {}
        
        # 统计信息
        self.stats = {
            'total_received': 0,
            'total_processed': 0,
            'total_failed': 0,
            'queue_size': 0,
            'processing_time_avg': 0.0
        }
        
        # 工作协程列表
        self.workers = []
        self.running = False
        
        # 死信队列（处理失败的消息）
        self.dead_letter_queue = asyncio.Queue(maxsize=100)
        
        logger.info(f"消息队列初始化完成 - 最大队列大小: {max_queue_size}, 工作协程数: {max_workers}")
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        self.handlers[message_type] = handler
        logger.info(f"已注册 {message_type.value} 类型消息处理器")
    
    def classify_message(self, raw_data: Dict[str, Any]) -> tuple[MessageType, MessagePriority]:
        """分类消息类型和优先级"""
        try:
            # 心跳消息
            if self._is_heartbeat_message(raw_data):
                return MessageType.HEARTBEAT, MessagePriority.LOW
            
            # 检查是否为同步包消息
            if not self._is_sync_package(raw_data):
                return MessageType.SYSTEM, MessagePriority.HIGH
            
            # 尝试解密和分析消息内容
            sync_data = raw_data.get("body", {}).get("syncPushPackage", {}).get("data", [])
            if not sync_data:
                return MessageType.SYSTEM, MessagePriority.HIGH
            
            # 这里可以根据解密后的内容进一步分类
            # 订单消息（高优先级）
            if self._is_order_message(raw_data):
                return MessageType.ORDER, MessagePriority.HIGH
            
            # 输入状态消息（低优先级）
            if self._is_typing_message(raw_data):
                return MessageType.TYPING, MessagePriority.LOW
            
            # 聊天消息（普通优先级）
            if self._is_chat_message(raw_data):
                return MessageType.CHAT, MessagePriority.NORMAL
            
            return MessageType.UNKNOWN, MessagePriority.NORMAL
            
        except Exception as e:
            logger.warning(f"消息分类失败: {e}")
            return MessageType.UNKNOWN, MessagePriority.NORMAL
    
    def _is_heartbeat_message(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为心跳消息"""
        return raw_data.get("code") == 200 and "body" not in raw_data
    
    def _is_sync_package(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为同步包消息"""
        return (
            "body" in raw_data and 
            "syncPushPackage" in raw_data["body"] and 
            "data" in raw_data["body"]["syncPushPackage"]
        )
    
    def _is_order_message(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为订单消息"""
        # 这里需要根据实际的订单消息特征来判断
        # 可以通过解密后的内容中的特定字段来判断
        return False  # 暂时返回False，需要根据实际情况实现
    
    def _is_typing_message(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为输入状态消息"""
        # 根据实际的输入状态消息特征来判断
        return False  # 暂时返回False，需要根据实际情况实现
    
    def _is_chat_message(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为聊天消息"""
        # 根据实际的聊天消息特征来判断
        return self._is_sync_package(raw_data)
    
    async def put_message(self, raw_data: Dict[str, Any], websocket: Any) -> bool:
        """将消息放入队列（生产者）"""
        try:
            # 分类消息
            message_type, priority = self.classify_message(raw_data)
            
            # 创建队列消息对象
            queued_message = QueuedMessage(
                id=f"{int(time.time() * 1000000)}_{hash(str(raw_data)) % 10000}",
                message_type=message_type,
                priority=priority,
                raw_data=raw_data,
                websocket=websocket,
                timestamp=time.time()
            )
            
            # 检查队列是否已满
            if self.queue.full():
                logger.warning("消息队列已满，丢弃最旧的消息")
                try:
                    # 非阻塞地获取一个消息并丢弃
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    pass
            
            # 将消息放入队列
            await self.queue.put((priority.value, time.time(), queued_message))
            
            # 更新统计
            self.stats['total_received'] += 1
            self.stats['queue_size'] = self.queue.qsize()
            
            logger.debug(f"消息已入队 - 类型: {message_type.value}, 优先级: {priority.value}, 队列大小: {self.queue.qsize()}")
            return True
            
        except Exception as e:
            logger.error(f"消息入队失败: {e}")
            return False
    
    async def _worker(self, worker_id: int):
        """工作协程（消费者）"""
        logger.info(f"消息处理工作协程 {worker_id} 已启动")
        
        while self.running:
            try:
                # 从队列获取消息（阻塞等待）
                priority, timestamp, queued_message = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                
                start_time = time.time()
                
                try:
                    # 查找对应的处理器
                    handler = self.handlers.get(queued_message.message_type)
                    if handler:
                        # 调用处理器
                        await handler(queued_message.raw_data, queued_message.websocket)
                        
                        # 更新统计
                        processing_time = time.time() - start_time
                        self.stats['total_processed'] += 1
                        self.stats['processing_time_avg'] = (
                            (self.stats['processing_time_avg'] * (self.stats['total_processed'] - 1) + processing_time) 
                            / self.stats['total_processed']
                        )
                        
                        logger.debug(f"工作协程 {worker_id} 处理消息完成 - 类型: {queued_message.message_type.value}, 耗时: {processing_time:.3f}s")
                    else:
                        logger.warning(f"未找到 {queued_message.message_type.value} 类型的消息处理器")
                        
                except Exception as e:
                    logger.error(f"工作协程 {worker_id} 处理消息失败: {e}")
                    
                    # 重试逻辑
                    queued_message.retry_count += 1
                    if queued_message.retry_count < queued_message.max_retries:
                        logger.info(f"消息重试 {queued_message.retry_count}/{queued_message.max_retries}")
                        await self.queue.put((priority, time.time(), queued_message))
                    else:
                        # 放入死信队列
                        try:
                            await self.dead_letter_queue.put(queued_message)
                            logger.warning(f"消息处理失败，已放入死信队列 - ID: {queued_message.id}")
                        except asyncio.QueueFull:
                            logger.error("死信队列已满，丢弃失败消息")
                        
                        self.stats['total_failed'] += 1
                
                finally:
                    # 标记任务完成
                    self.queue.task_done()
                    self.stats['queue_size'] = self.queue.qsize()
                    
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                logger.error(f"工作协程 {worker_id} 发生未知错误: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"消息处理工作协程 {worker_id} 已停止")
    
    async def start(self):
        """启动消息队列处理"""
        if self.running:
            logger.warning("消息队列已在运行中")
            return
        
        self.running = True
        
        # 启动工作协程
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
        
        logger.info(f"消息队列已启动 - {self.max_workers} 个工作协程")
    
    async def stop(self):
        """停止消息队列处理"""
        if not self.running:
            return
        
        logger.info("正在停止消息队列...")
        self.running = False
        
        # 等待所有工作协程完成
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
        
        logger.info("消息队列已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            **self.stats,
            'queue_size': self.queue.qsize(),
            'dead_letter_queue_size': self.dead_letter_queue.qsize(),
            'running': self.running,
            'workers_count': len(self.workers)
        }
    
    async def get_dead_letter_messages(self, max_count: int = 10) -> list:
        """获取死信队列中的消息"""
        messages = []
        count = 0
        
        while count < max_count and not self.dead_letter_queue.empty():
            try:
                message = self.dead_letter_queue.get_nowait()
                messages.append({
                    'id': message.id,
                    'type': message.message_type.value,
                    'retry_count': message.retry_count,
                    'timestamp': message.timestamp,
                    'raw_data': message.raw_data
                })
                count += 1
            except asyncio.QueueEmpty:
                break
        
        return messages 