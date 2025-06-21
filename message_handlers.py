import asyncio
import json
import time
import base64
from typing import Dict, Any
from loguru import logger
from datetime import datetime

from utils.xianyu_utils import decrypt
from XianyuAgent import XianyuReplyBot
from context_manager import ChatContextManager


class MessageHandlers:
    """消息处理器集合"""
    
    def __init__(self, xianyu_live_instance=None):
        """
        初始化消息处理器
        
        Args:
            xianyu_live_instance: XianyuLive实例，可选参数
        """
        self.xianyu_live = xianyu_live_instance
        logger.info("消息处理器初始化完成")
    
    async def handle_heartbeat(self, raw_data: Dict[str, Any], websocket: Any):
        """处理心跳消息"""
        try:
            # 调用原有的心跳处理逻辑
            await self.xianyu_live.handle_heartbeat_response(raw_data)
            logger.debug("心跳消息处理完成")
        except Exception as e:
            logger.error(f"心跳消息处理失败: {e}")
            raise
    
    async def handle_system(self, raw_data: Dict[str, Any], websocket: Any):
        """处理系统消息"""
        try:
            logger.debug("处理系统消息")
            
            # 发送通用ACK响应
            if "headers" in raw_data and "mid" in raw_data["headers"]:
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": raw_data["headers"]["mid"],
                        "sid": raw_data["headers"].get("sid", "")
                    }
                }
                # 复制其他可能的header字段
                for key in ["app-key", "ua", "dt"]:
                    if key in raw_data["headers"]:
                        ack["headers"][key] = raw_data["headers"][key]
                await websocket.send(json.dumps(ack))
            
            logger.debug("系统消息处理完成")
        except Exception as e:
            logger.error(f"系统消息处理失败: {e}")
            raise
    
    async def handle_typing(self, raw_data: Dict[str, Any], websocket: Any):
        """处理输入状态消息"""
        try:
            logger.debug("用户正在输入")
            # 这里可以添加语音提醒或其他逻辑
            self.xianyu_live.engine.say("用户正在输入")

            self.xianyu_live.engine.runAndWait()
        except Exception as e:
            logger.error(f"输入状态消息处理失败: {e}")
            raise
    
    async def handle_order(self, raw_data: Dict[str, Any], websocket: Any):
        """处理订单消息"""
        try:
            logger.info("处理订单消息")
            
            # 解密消息内容
            decrypted_message = await self._decrypt_message(raw_data)
            if not decrypted_message:
                return
        
            # 处理订单相关逻辑
            await self._process_order_message(decrypted_message, websocket)
            
        except Exception as e:
            logger.error(f"订单消息处理失败: {e}")
            raise
    
    async def handle_chat(self, raw_data: Dict[str, Any], websocket: Any):
        """处理聊天消息"""
        try:
            logger.debug("处理聊天消息")
            
            # 发送ACK响应
            await self._send_ack(raw_data, websocket)
            
            # 检查是否为同步包消息
            if not self._is_sync_package(raw_data):
                return
            
            # 解密消息内容
            decrypted_message = await self._decrypt_message(raw_data)
            if not decrypted_message:
                return
            
            # 处理订单消息
            if await self._process_order_message(decrypted_message, websocket):
                return
            
            # 处理输入状态
            if self._is_typing_status(decrypted_message):
                logger.debug("用户正在输入")
                # 安全的语音提醒处理
                try:
                    # 检查是否有语音引擎可用
                    if hasattr(self.xianyu_live, 'engine') and self.xianyu_live.engine:
                        self.xianyu_live.engine.say("用户正在输入")
                        self.xianyu_live.engine.runAndWait()
                    else:
                        # 如果没有语音引擎，可以使用全局的语音引擎
                        import main
                        if hasattr(main, 'engine') and main.engine:
                            main.engine.say("用户正在输入")
                            main.engine.runAndWait()
                        else:
                            logger.debug("语音引擎不可用，跳过语音提醒")
                except Exception as e:
                    logger.warning(f"语音提醒失败: {e}")
                return
            
            # 处理聊天消息
            if not self._is_chat_message_content(decrypted_message):
                logger.debug("非聊天消息内容")
                return
            
            # 处理具体的聊天逻辑
            await self._process_chat_message(decrypted_message, websocket)
            
        except Exception as e:
            logger.error(f"聊天消息处理失败: {e}")
            raise
    
    async def handle_unknown(self, raw_data: Dict[str, Any], websocket: Any):
        """处理未知类型消息"""
        try:
            logger.warning("处理未知类型消息")
            logger.debug(f"未知消息内容: {raw_data}")
            
            # 尝试发送ACK响应
            await self._send_ack(raw_data, websocket)
            
        except Exception as e:
            logger.error(f"未知消息处理失败: {e}")
            raise
    
    async def _send_ack(self, raw_data: Dict[str, Any], websocket: Any):
        """发送ACK响应"""
        try:
            if "headers" in raw_data and "mid" in raw_data["headers"]:
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": raw_data["headers"]["mid"],
                        "sid": raw_data["headers"].get("sid", "")
                    }
                }
                # 复制其他可能的header字段
                for key in ["app-key", "ua", "dt"]:
                    if key in raw_data["headers"]:
                        ack["headers"][key] = raw_data["headers"][key]
                await websocket.send(json.dumps(ack))
        except Exception as e:
            logger.warning(f"发送ACK失败: {e}")
    
    def _is_sync_package(self, raw_data: Dict[str, Any]) -> bool:
        """判断是否为同步包消息"""
        return (
            "body" in raw_data and 
            "syncPushPackage" in raw_data["body"] and 
            "data" in raw_data["body"]["syncPushPackage"]
        )
    
    async def _decrypt_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """解密消息"""
        try:
            sync_data = raw_data["body"]["syncPushPackage"]["data"][0]
            
            if "data" not in sync_data:
                logger.debug("同步包中无data字段")
                return None
            
            data = sync_data["data"]
            
            # 尝试直接解析JSON
            try:
                data = base64.b64decode(data).decode("utf-8")
                message = json.loads(data)
                logger.info(f"无需解密 message: {message}")
                return message
            except Exception:
                # 需要解密
                try:
                    decrypted_data = decrypt(data)
                    message = json.loads(decrypted_data)
                    logger.debug("消息解密成功")
                    return message
                except Exception as e:
                    logger.error(f"消息解密失败: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"消息解密过程失败: {e}")
            return None
    
    async def _process_order_message(self, message: Dict[str, Any], websocket: Any) -> bool:

        print("**")
        print("解密消息：")
        print(message)
        print("**")

        """处理订单消息，返回是否为订单消息"""
        try:
            # 检查是否为订单消息
            if '3' not in message or not isinstance(message['3'], dict) or 'redReminder' not in message['3']:
                return False
            
            red_reminder = message['3']['redReminder']
            
            # 安全地提取用户ID，处理不同的数据结构
            user_id = None
            if '1' in message:
                field_1 = message['1']
                if isinstance(field_1, str) and '@' in field_1:
                    user_id = field_1.split('@')[0]
                elif isinstance(field_1, dict) and '1' in field_1 and isinstance(field_1['1'], dict) and '1' in field_1['1']:
                    # 处理嵌套结构 {'1': {'1': '4064106662@goofish'}}
                    nested_field = field_1['1']['1']
                    if isinstance(nested_field, str) and '@' in nested_field:
                        user_id = nested_field.split('@')[0]
            
            if not user_id:
                logger.debug("无法从订单消息中提取用户ID")
                return False
                
            user_url = f'https://www.goofish.com/personal?userId={user_id}'
            
            if red_reminder == '等待买家付款':
                logger.info(f'等待买家 {user_url} 付款')
                return True
            elif red_reminder == '交易关闭':
                logger.info(f'买家 {user_url} 交易关闭')
                return True
            elif red_reminder == '等待卖家发货':
                logger.info(f'交易成功 {user_url} 等待卖家发货')
                
                # 发送ToDesk下载地址
                msg_todesk = "todesk 下载地址：https://dl.todesk.com/windows/ToDesk_Setup.exe"
                
                # 安全地提取chat_id和send_user_id
                chat_id = None
                send_user_id = None
                
                if isinstance(message.get('1'), dict) and '2' in message['1']:
                    chat_field = message['1']['2']
                    if isinstance(chat_field, str) and '@' in chat_field:
                        chat_id = chat_field.split('@')[0]
                
                if isinstance(message.get('1'), dict) and '10' in message['1'] and 'senderUserId' in message['1']['10']:
                    send_user_id = message['1']['10']['senderUserId']
                
                if chat_id and send_user_id:
                    await self.xianyu_live.send_msg(websocket, chat_id, send_user_id, msg_todesk)
                    logger.info("已发送ToDesk下载地址")
                else:
                    logger.warning("无法提取chat_id或send_user_id，跳过发送ToDesk地址")
                    
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"订单消息处理失败: {e}")
            return False
    
    def _is_typing_status(self, message: Dict[str, Any]) -> bool:
        """判断是否为输入状态消息"""
        return self.xianyu_live.is_typing_status(message)
    
    def _is_chat_message_content(self, message: Dict[str, Any]) -> bool:
        """判断是否为聊天消息内容"""
        return self.xianyu_live.is_chat_message(message)
    
    async def _process_chat_message(self, message: Dict[str, Any], websocket: Any):
        """处理具体的聊天消息"""
        try:
            # 提取消息信息
            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]
            
            # 时效性验证（过滤5分钟前消息）
            if (time.time() * 1000 - create_time) > self.xianyu_live.message_expire_time:
                logger.debug("过期消息丢弃")
                return
            
            # 获取商品ID和会话ID
            url_info = message["1"]["10"]["reminderUrl"]
            item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
            chat_id = message["1"]["2"].split('@')[0]
            
            if not item_id:
                logger.warning("无法获取商品ID")
                return
            
            # 检查是否为卖家（自己）发送的控制命令
            if send_user_id == self.xianyu_live.myid:
                await self._handle_seller_message(send_message, chat_id, item_id)
                return
            
            # 处理新用户消息
            await self._handle_new_user_message(
                send_user_id, send_user_name, send_message, 
                chat_id, item_id, websocket
            )
            
            # 打印消息信息
            import main
            #main.process_and_print_message_info(message)

            
            print("用户：")
            print(f"用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}, 消息: {send_message}")
            print("**" * 10)
            
            # 处理特殊消息
            special_handled = await self._handle_special_messages(send_message, chat_id, send_user_id, websocket)
            
            # 如果特殊消息已被处理（如ping命令），则不再执行AI回复
            if special_handled:
                logger.info(f"特殊消息已处理，跳过AI回复生成")
                return

            # 添加用户消息到上下文
            self.xianyu_live.context_manager.add_message_by_chat(
                chat_id, send_user_id, item_id, "user", send_message
            )
            
            # 如果当前会话处于人工接管模式，不进行自动回复
            if self.xianyu_live.is_manual_mode(chat_id):
                logger.info(f"🔴 会话 {chat_id} 处于人工接管模式，跳过自动回复")
                return
            
            if self.xianyu_live.is_system_message(message):
                logger.debug("系统消息，跳过处理")
                return
            
            # 生成AI回复
            await self._generate_ai_reply(
                send_user_name, send_message, chat_id, 
                item_id, send_user_id, websocket
            )
            
        except Exception as e:
            logger.error(f"聊天消息处理失败: {e}")
            raise
    
    async def _handle_seller_message(self, send_message: str, chat_id: str, item_id: str):
        """处理卖家消息"""
        logger.debug("检测到卖家消息，检查是否为控制命令")
        
        # 检查切换命令
        if self.xianyu_live.check_toggle_keywords(send_message):
            mode = self.xianyu_live.toggle_manual_mode(chat_id)
            if mode == "manual":
                logger.info(f"🔴 已接管会话 {chat_id} (商品: {item_id})")
            else:
                logger.info(f"🟢 已恢复会话 {chat_id} 的自动回复 (商品: {item_id})")
            return
        
        # 记录卖家人工回复
        self.xianyu_live.context_manager.add_message_by_chat(
            chat_id, self.xianyu_live.myid, item_id, "assistant", send_message
        )
        logger.info(f"卖家人工回复 (会话: {chat_id}, 商品: {item_id}): {send_message}")
    
    async def _handle_new_user_message(
        self, send_user_id: str, send_user_name: str, send_message: str,
        chat_id: str, item_id: str, websocket: Any
    ):
        """处理新用户消息"""
        try:
            if not self.xianyu_live:
                logger.warning("XianyuLive实例未初始化，跳过用户消息处理")
                return
                
            # 检查是否为人工接管模式的切换关键词
            if self.xianyu_live.check_toggle_keywords(send_message):
                self.xianyu_live.toggle_manual_mode(chat_id)
                return

            # 检查是否处于人工接管模式
            if self.xianyu_live.is_manual_mode(chat_id):
                logger.info(f"会话 {chat_id} 处于人工接管模式，跳过自动回复")
                return

            # 检查数据库中是否已存在该用户的记录
            import main
            if not main.check_user_exists_in_messages("data/chat_history.db", send_user_id):
                logger.info(f"新用户 {send_user_name}({send_user_id}) 首次发送消息")
                
                # 发送邮件通知
                subject = f"新用户消息通知 - {send_user_name}"
                content = f"""
                用户信息：
                - 用户名：{send_user_name}
                - 用户ID：{send_user_id}
                - 会话ID：{chat_id}
                - 商品ID：{item_id}
                - 消息内容：{send_message}
                - 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                try:
                    main.send_email_notification(
                        subject, content, 
                        main.sender, main.recver, main.password
                    )
                    logger.info("新用户邮件通知发送成功")
                except Exception as e:
                    logger.error(f"发送邮件通知失败: {e}")

            # 注意：不在这里调用AI回复生成，避免重复处理
            # AI回复生成将在_process_chat_message方法中统一处理

        except Exception as e:
            logger.error(f"处理新用户消息失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_special_messages(
        self, send_message: str, chat_id: str, send_user_id: str, websocket: Any
    ):
        """处理特殊消息"""
        try:
         
            # 处理ping命令 - 测试机器人是否正常运行
            if send_message.strip().lower() == "/ping":
                pong_reply = "pong 🏓 机器人运行正常！"
                await self.xianyu_live.send_msg(websocket, chat_id, send_user_id, pong_reply)
                logger.info(f"响应ping命令，发送pong回复给用户 {send_user_id}")
                return True  # 返回True表示已处理特殊命令

    

            # 处理付款消息
            if "我已付款，等待你发货" in send_message:
                msg_todesk = "你好，todesk 下载地址：https://dl.todesk.com/windows/ToDesk_Setup.exe"
                await self.xianyu_live.send_msg(websocket, chat_id, send_user_id, msg_todesk)
                return True  # 返回True表示已处理特殊命令
            
            # 处理交易完成消息
            if ("买家确认收货，交易成功" in send_message or 
                "快给ta一个评价吧～" in send_message):
                msg_review = "可以的话 辛苦带图好评，谢谢支持"
                await self.xianyu_live.send_msg(websocket, chat_id, send_user_id, msg_review)
                await asyncio.sleep(2)
                return True  # 返回True表示已处理特殊命令
            
            return False  # 返回False表示没有处理特殊命令
                
        except Exception as e:
            logger.error(f"特殊消息处理失败: {e}")
            return False
    
    async def _generate_ai_reply(
        self, send_user_name: str, send_message: str, chat_id: str,
        item_id: str, send_user_id: str, websocket: Any
    ):
        """生成AI回复"""
        try:
            if not self.xianyu_live:
                logger.warning("XianyuLive实例未初始化，无法生成AI回复")
                return
                
            # 从数据库获取商品信息
            logger.info(f"从数据库获取商品信息: {item_id}")
            item_info = self.xianyu_live.context_manager.get_item_info(item_id)
            if not item_info:
                logger.warning(f"未找到商品信息: {item_id}")
                return

            item_description = item_info.get('title', '未知商品')

            # 获取对话历史
            context = self.xianyu_live.context_manager.get_context_by_chat(chat_id)
            
            # 生成回复
            bot_reply = self.xianyu_live.bot.generate_reply(
                send_message,
                item_description,
                context
            )

            if not bot_reply or bot_reply.strip() == "":
                logger.warning("AI生成的回复为空")
                return

            # 检查是否为价格意图，如果是则增加议价次数
            if self.xianyu_live.bot.last_intent == "price":
                self.xianyu_live.context_manager.increment_bargain_count_by_chat(chat_id)
                bargain_count = self.xianyu_live.context_manager.get_bargain_count_by_chat(chat_id)
                logger.info(f"议价次数增加到: {bargain_count}")

            # 保存对话历史
            self.xianyu_live.context_manager.add_message_by_chat(
                chat_id, send_user_id, item_id, "user", send_message
            )
            self.xianyu_live.context_manager.add_message_by_chat(
                chat_id, self.xianyu_live.myid, item_id, "assistant", bot_reply
            )

            # 发送回复
            logger.info(f"准备发送AI回复: {bot_reply}")
            #await self.xianyu_live.send_msg(websocket, chat_id, send_user_id, bot_reply)

            logger.info("AI回复发送成功")

        except Exception as e:
            logger.error(f"AI回复生成失败: {e}")
            import traceback
            traceback.print_exc() 