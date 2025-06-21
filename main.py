import base64
import json
import asyncio
import time
import os
import websockets
from loguru import logger
from dotenv import load_dotenv
from XianyuApis import XianyuApis
import sys
import pyttsx3

# 导入消息队列相关模块
from message_queue import MessageQueue, MessageType
from message_handlers import MessageHandlers

import requests
import json
from datetime import datetime
import re # 引入正则表达式模块，用于更健壮地解析URL


engine = pyttsx3.init()


from utils.xianyu_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt
from XianyuAgent import XianyuReplyBot
from context_manager import ChatContextManager

import smtplib
from email.mime.text import MIMEText
subject = "新顾客消息通知"

sender = "@163.com"
recver = "@qq.com"
password = ""

def get_ip_info(ip_address):
    """
    通过调用第三方API获取IP地址的相关信息。
    """
    url = f"http://ip-api.com/json/{ip_address}?lang=zh-CN"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            # 精简返回信息以便于打印
            info = {
                "国家": data.get('country', 'N/A'),
                "地区": data.get('regionName', 'N/A'),
                "城市": data.get('city', 'N/A'),
                "ISP": data.get('isp', 'N/A'),
            }
            return info
        else:
            return {"error": f"API查询失败: {data.get('message', '未知错误')}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"网络请求或API错误: {e}"}
    except Exception as e:
        return {"error": f"发生未知错误: {e}"}


# --- 升级后的处理与打印函数 ---
def process_and_print_message_info(message_data: dict):
    """
    全面解析消息对象，分门别类地打印所有有用的信息。

    Args:
        message_data (dict): 单条消息的数据字典。
    """
    print("=" * 50)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始处理新消息")
    print("=" * 50)

    try:
        # --- 安全地提取各层级的数据 ---
        info_layer_1 = message_data.get('1', {})
        message_core = info_layer_1.get('6', {}).get('3', {})
        meta_info = info_layer_1.get('10', {})
        push_info = message_data.get('3', {})

        # --- 1. 基本信息提取 ---
        sender_id = meta_info.get('senderUserId', '未提供')
        sender_nickname = meta_info.get('reminderTitle', '未提供').strip()  # .strip()去除可能的前后空格
        chat_id_full = info_layer_1.get('2', '')
        chat_id = chat_id_full.split('@')[0] if '@' in chat_id_full else '未提供'

        # 解析 reminderUrl 获取 itemId
        item_id = '未提供'
        url_info = meta_info.get('reminderUrl', '')
        if "itemId=" in url_info:
            # 使用正则表达式更安全地提取
            match = re.search(r'itemId=(\d+)', url_info)
            if match:
                item_id = match.group(1)

        print("--- 基本信息 ---")
        print(f"{'发信人ID':<12}: {sender_id}")
        print(f"{'发信人昵称':<12}: {sender_nickname}")
        print(f"{'会话ID':<12}: {chat_id}")
        print(f"{'关联商品ID':<12}: {item_id}")

        # --- 2. 消息详情提取 ---
        msg_type_id = message_core.get('4')
        content_payload_str = message_core.get('5', '{}')
        content_payload = json.loads(content_payload_str)

        # 解析 bizTag 获取服务端 messageId
        server_msg_id = '未提供'
        try:
            biz_tag_json = json.loads(meta_info.get('bizTag', '{}'))
            server_msg_id = biz_tag_json.get('messageId', '未提供')
        except json.JSONDecodeError:
            pass  # 如果解析失败，保持默认值

        client_msg_id = info_layer_1.get('3', '未提供')
        timestamp_ms = info_layer_1.get('5', 0)
        message_time = datetime.fromtimestamp(timestamp_ms / 1000).strftime(
            '%Y-%m-%d %H:%M:%S') if timestamp_ms else '未提供'

        print("\n--- 消息详情 ---")
        print(f"{'消息时间':<12}: {message_time}")
        print(f"{'服务端消息ID':<12}: {server_msg_id}")
        print(f"{'客户端消息ID':<12}: {client_msg_id}")

        if msg_type_id == 1:
            text_content = content_payload.get('text', {}).get('text', '无法提取文本')
            print(f"{'消息类型':<12}: 纯文本")
            print(f"{'内容':<12}: {text_content}")
        elif msg_type_id == 2:
            image_url = '无法提取'
            try:
                image_url = content_payload['image']['pics'][0]['url']
            except (KeyError, IndexError):
                pass
            print(f"{'消息类型':<12}: 图片")
            print(f"{'图片URL':<12}: {image_url}")
        elif msg_type_id == 5:
            expression_name = content_payload.get('expression', {}).get('name', '未知表情')
            print(f"{'消息类型':<12}: 表情")
            print(f"{'表情名称':<12}: {expression_name}")
        else:
            print(f"{'消息类型':<12}: 未知 (类型ID: {msg_type_id})")

        # --- 3. 技术与网络信息 ---
        platform = meta_info.get('_platform', '未提供')
        ip_address = meta_info.get('clientIp', '未提供')
        port = meta_info.get('port', '未提供')
        need_push = push_info.get('needPush', '未知')

        print("\n--- 技术与网络信息 ---")
        print(f"{'发送平台':<12}: {platform}")
        print(f"{'客户端IP':<12}: {ip_address}")
        print(f"{'客户端端口':<12}: {port}")
        print(f"{'需要推送通知':<12}: {need_push}")

        if ip_address != '未提供':
            ip_info = get_ip_info(ip_address)
            print(f"{'IP地理位置':<12}: ", end="")
            if 'error' in ip_info:
                print(f"查询失败 - {ip_info['error']}")
            else:
                # 格式化地理位置信息在一行显示
                location_str = f"{ip_info.get('国家')} {ip_info.get('地区')} {ip_info.get('城市')} ({ip_info.get('ISP')})"
                print(location_str)

        # --- 4. 原始元数据 ---
        print("\n--- 原始元数据 ---")
        print(f"{'Reminder URL':<12}: {url_info}")

    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        print(f"\n处理消息时发生严重错误：数据结构异常或解析失败。")
        print(f"错误类型: {type(e).__name__}, 错误详情: {e}")
    finally:
        print("=" * 50 + "\n")




def send_email_notification(subject, content, sender, recver, password):
    """
    Sends an email notification.

    :param subject: The subject of the email.
    :param content: The content of the email.
    :param sender: The sender's email address.
    :param recver: The receiver's email address.
    :param password: The password for the sender's email.
    """
    # Create the email message
    message = MIMEText(content, "plain", "utf-8")
    message['Subject'] = subject
    message['To'] = recver
    message['From'] = sender

    try:
        # Connect to the SMTP server and send the email
        smtp = smtplib.SMTP_SSL("smtp.163.com", 994)
        smtp.login(sender, password)
        smtp.sendmail(sender, [recver], message.as_string())
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")
    finally:
        smtp.quit()





import sqlite3
import os # 导入 os 模块，用于处理文件路径，虽然这里直接用字符串路径也可以
msg_list_expanded = [
    "你好", "您好", "老板", "在吗", "有人", "1", "哈喽", "Hi", "你好呀", "hi", "方便", "标价", "拍", "在", "看看", "了解", "请问", "这个", "请问", "直接", "咨询"
]
msg_list_2_expanded = ["报错","问题","解决","pip","vscode","pycharm","可以","作业","调试","代码","程序","运行","环境","安装","配置","异常","错误","bug","不了","不对","卡","python","库","模块","终端","命令行","依赖","怎么","如何","不会","为什么","看下","帮忙","求助","作业","写代码","实现","功能","远程","todesk","向日葵"]

def check_user_exists_in_messages(db_path: str, user_id_to_check: str) -> bool:
    """
    检查给定用户ID是否存在于SQLite数据库的'messages'表中。

    参数:
        db_path (str): SQLite数据库文件的路径 (例如: 'data/chat_history.db')。
                       这个路径是相对于运行脚本的当前工作目录。
        user_id_to_check (str): 要在'user_id'列中搜索的用户ID字符串。

    返回:
        bool: 如果在'messages'表中找到该用户ID，则返回True；否则返回False。
              如果在数据库连接或查询过程中发生错误，也返回False。
    """
    conn = None # 初始化数据库连接变量
    try:
        # 构建数据库文件的完整路径 (如果需要，这里使用了os.path.join)
        # 但对于相对路径 'data/chat_history.db'，直接使用字符串也是可以的。
        # 假设你的脚本和data文件夹在同一级，数据库文件在data文件夹内。
        # full_db_path = os.path.join('.', db_path) # '.' 表示当前目录

        # 连接到SQLite数据库
        # 使用提供的相对路径连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor() # 创建一个游标对象，用于执行SQL命令

        # SQL查询语句：检查 messages 表中是否存在 user_id 等于给定值的记录
        # SELECT 1 是一种高效的方式，因为它只关心是否有匹配的行存在，不关心具体数据。
        # LIMIT 1 找到第一条匹配记录后就停止搜索，提高效率。
        query = "SELECT 1 FROM messages WHERE user_id = ? LIMIT 1"

        # 执行查询。将 user_id_to_check 作为参数传递 (必须是一个元组)，
        # 这是防止SQL注入的标准做法。
        cursor.execute(query, (user_id_to_check,))

        # 获取查询结果的下一行。
        # 如果找到了匹配的记录，fetchone() 会返回一行数据（这里是 (1,)）。
        # 如果没有找到匹配的记录，fetchone() 会返回 None。
        result = cursor.fetchone()

        # 判断结果是否为 None。如果不是 None，说明找到了记录，返回 True。
        # 如果是 None，说明没有找到记录，返回 False。
        return result is not None

    except sqlite3.Error as e:
        # 捕获并处理数据库操作中可能发生的错误
        # 例如：数据库文件不存在、表不存在、权限问题等
        print(f"检查用户ID '{user_id_to_check}' 是否存在时发生数据库错误: {e}")
        # 在错误发生时，我们无法确定用户是否存在，所以返回 False 是一个安全的做法。
        return False
    finally:
        # 无论是否发生异常，都确保关闭数据库连接
        if conn:
            conn.close() # 关闭连接释放资源


class XianyuLive:
    def __init__(self, cookies_str):
        self.xianyu = XianyuApis()
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies_str = cookies_str
        self.cookies = trans_cookies(cookies_str)
        self.xianyu.session.cookies.update(self.cookies)  # 直接使用 session.cookies.update
        self.myid = self.cookies['unb']
        self.device_id = generate_device_id(self.myid)
        
        # 初始化上下文管理器
        self.context_manager = ChatContextManager()

        # 心跳相关配置
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "15"))  # 心跳间隔，默认15秒
        self.heartbeat_timeout = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))     # 心跳超时，默认5秒
        self.last_heartbeat_time = 0
        self.last_heartbeat_response = 0
        self.heartbeat_task = None
        self.ws = None

        # Token刷新相关配置
        self.token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", "1800"))  # Token刷新间隔，默认1小时
        self.token_retry_interval = int(os.getenv("TOKEN_RETRY_INTERVAL", "150"))       # Token重试间隔，默认5分钟
        self.last_token_refresh_time = 0
        self.current_token = None
        self.token_refresh_task = None
        self.connection_restart_flag = False  # 连接重启标志

        # 人工接管相关配置
        self.manual_mode_conversations = set()  # 存储处于人工接管模式的会话ID
        self.manual_mode_timeout = int(os.getenv("MANUAL_MODE_TIMEOUT", "3600"))  # 人工接管超时时间，默认1小时
        self.manual_mode_timestamps = {}  # 记录进入人工模式的时间

        # 消息过期时间配置
        self.message_expire_time = int(os.getenv("MESSAGE_EXPIRE_TIME", "300000"))  # 消息过期时间，默认5分钟

        # 人工接管关键词，从环境变量读取
        self.toggle_keywords = os.getenv("TOGGLE_KEYWORDS", "。")

        # 初始化AI机器人
        self.bot = XianyuReplyBot()

        # 初始化消息队列系统
        self.message_queue = MessageQueue(max_queue_size=1000, max_workers=7)
        self.message_handlers = MessageHandlers(self)
        self._register_message_handlers()
        
        logger.info(f"消息队列系统初始化完成 - 队列大小: 1000, 工作协程数: 7")

    def _register_message_handlers(self):
        """注册各种类型的消息处理器"""
        self.message_queue.register_handler(MessageType.HEARTBEAT, self.message_handlers.handle_heartbeat)
        self.message_queue.register_handler(MessageType.SYSTEM, self.message_handlers.handle_system)
        self.message_queue.register_handler(MessageType.CHAT, self.message_handlers.handle_chat)
        self.message_queue.register_handler(MessageType.TYPING, self.message_handlers.handle_typing)
        self.message_queue.register_handler(MessageType.ORDER, self.message_handlers.handle_order)
        self.message_queue.register_handler(MessageType.UNKNOWN, self.message_handlers.handle_unknown)

    async def refresh_token(self):
        """刷新token"""
        try:
            logger.info("开始刷新token...")

            # 获取新token（如果Cookie失效，get_token会直接退出程序）
            token_result = self.xianyu.get_token(self.device_id)
            if 'data' in token_result and 'accessToken' in token_result['data']:
                new_token = token_result['data']['accessToken']
                self.current_token = new_token
                self.last_token_refresh_time = time.time()
                logger.info("Token刷新成功")
                return new_token
            else:
                logger.error(f"Token刷新失败: {token_result}")
                return None

        except Exception as e:
            logger.error(f"Token刷新异常: {str(e)}")
            return None

    async def token_refresh_loop(self):
        """Token刷新循环"""
        while True:
            try:
                current_time = time.time()
                # 检查是否需要刷新token
                if current_time - self.last_token_refresh_time >= self.token_refresh_interval:
                    logger.info("Token即将过期，准备刷新...")

                    new_token = await self.refresh_token()
                    if new_token:
                        logger.info("Token刷新成功，准备重新建立连接...")
                        # 设置连接重启标志
                        self.connection_restart_flag = True
                        # 关闭当前WebSocket连接，触发重连
                        if self.ws:
                            await self.ws.close()
                        break
                    else:
                        logger.error("Token刷新失败，将在{}分钟后重试".format(self.token_retry_interval // 60))
                        await asyncio.sleep(self.token_retry_interval)  # 使用配置的重试间隔
                        continue

                # 每分钟检查一次
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Token刷新循环出错: {e}")
                await asyncio.sleep(60)

    async def send_msg(self, ws, cid, toid, text):
        text = {
            "contentType": 1,
            "text": {
                "text": text
            }
        }
        text_base64 = str(base64.b64encode(json.dumps(text).encode('utf-8')), 'utf-8')
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{cid}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {
                            "type": 1,
                            "data": text_base64
                        }
                    },
                    "redPointPolicy": 0,
                    "extension": {
                        "extJson": "{}"
                    },
                    "ctx": {
                        "appVersion": "1.0",
                        "platform": "web"
                    },
                    "mtags": {},
                    "msgReadStatusSetting": 1
                },
                {
                    "actualReceivers": [
                        f"{toid}@goofish",
                        f"{self.myid}@goofish"
                    ]
                }
            ]
        }
        await ws.send(json.dumps(msg))

    async def init(self, ws):
        # 如果没有token或者token过期，获取新token
        if not self.current_token or (time.time() - self.last_token_refresh_time) >= self.token_refresh_interval:
            logger.info("获取初始token...")
            await self.refresh_token()

        if not self.current_token:
            logger.error("无法获取有效token，初始化失败")
            raise Exception("Token获取失败")

        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": self.current_token,
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid()
            }
        }
        await ws.send(json.dumps(msg))
        # 等待一段时间，确保连接注册完成
        await asyncio.sleep(1)
        msg = {"lwp": "/r/SyncStatus/ackDiff", "headers": {"mid": "5701741704675979 0"}, "body": [
            {"pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync", "topic": "sync", "highPts": 0,
             "pts": int(time.time() * 1000) * 1000, "seq": 0, "timestamp": int(time.time() * 1000)}]}
        await ws.send(json.dumps(msg))
        logger.info('连接注册完成')

    def is_chat_message(self, message):
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], dict)  # 确保是字典类型
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)  # 确保是字典类型
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False

    def is_sync_package(self, message_data):
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False

    def is_typing_status(self, message):
        """判断是否为用户正在输入状态消息"""
        #参考实际消息
        #{'1': [{'1': '50974897393@goofish', '2': 1, '3': 0, '4': '3828637726@goofish'}]}


        res = (isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"])
        if(res==True):
            print("用户：{}，正在输入".format(message["1"][0]["1"]))
        try:
            return res
        except Exception:
            return False

    def is_system_message(self, message):
        """判断是否为系统消息"""
        try:
            return (
                isinstance(message, dict)
                and "3" in message
                and isinstance(message["3"], dict)
                and "needPush" in message["3"]
                and message["3"]["needPush"] == "false"
            )
        except Exception:
            return False

    def check_toggle_keywords(self, message):
        """检查消息是否包含切换关键词"""
        message_stripped = message.strip()
        return message_stripped in self.toggle_keywords

    def is_manual_mode(self, chat_id):
        """检查特定会话是否处于人工接管模式"""
        if chat_id not in self.manual_mode_conversations:
            return False

        # 检查是否超时
        current_time = time.time()
        if chat_id in self.manual_mode_timestamps:
            if current_time - self.manual_mode_timestamps[chat_id] > self.manual_mode_timeout:
                # 超时，自动退出人工模式
                self.exit_manual_mode(chat_id)
                return False
        return True

    def enter_manual_mode(self, chat_id):
        """进入人工接管模式"""
        self.manual_mode_conversations.add(chat_id)
        self.manual_mode_timestamps[chat_id] = time.time()

    def exit_manual_mode(self, chat_id):
        """退出人工接管模式"""
        self.manual_mode_conversations.discard(chat_id)
        if chat_id in self.manual_mode_timestamps:
            del self.manual_mode_timestamps[chat_id]

    def toggle_manual_mode(self, chat_id):
        """切换人工接管模式"""
        if self.is_manual_mode(chat_id):
            self.exit_manual_mode(chat_id)
            return "auto"
        else:
            self.enter_manual_mode(chat_id)
            return "manual"

    async def handle_message(self, message_data, websocket):
        """处理所有类型的消息"""
        try:
            try:
                message = message_data
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                        "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                    }
                }
                if 'app-key' in message["headers"]:
                    ack["headers"]["app-key"] = message["headers"]["app-key"]
                if 'ua' in message["headers"]:
                    ack["headers"]["ua"] = message["headers"]["ua"]
                if 'dt' in message["headers"]:
                    ack["headers"]["dt"] = message["headers"]["dt"]
                await websocket.send(json.dumps(ack))
            except Exception as e:
                pass

            # 如果不是同步包消息，直接返回
            if not self.is_sync_package(message_data):
                return

            # 获取并解密数据
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]

            # 检查是否有必要的字段
            if "data" not in sync_data:
                logger.debug("同步包中无data字段")
                return

            # 解密数据
            try:
                data = sync_data["data"]
                try:
                    data = base64.b64decode(data).decode("utf-8")
                    data = json.loads(data)
                    logger.info(f"无需解密 message: {data}")

                    return
                except Exception as e:
                    #logger.info(f'加密数据: {data}')

                    decrypted_data = decrypt(data)
                    message = json.loads(decrypted_data)
                    print("**"*10)
                    print("解密数据：")
                    print(message)
                    print("**"*10)
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return

            try:
                # 判断是否为订单消息,需要自行编写付款后的逻辑
                if message['3']['redReminder'] == '等待买家付款':
                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'等待买家 {user_url} 付款')
                    return
                elif message['3']['redReminder'] == '交易关闭':
                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'买家 {user_url} 交易关闭')
                    return
                elif message['3']['redReminder'] == '等待卖家发货':

                    print("**" * 10)
                    print("等待卖家发货：")
                    print(message_data)
                    print("**" * 10)


                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'交易成功 {user_url} 等待卖家发货')
                    msg_todesk = r"todesk 下载地址：https://dl.todesk.com/windows/ToDesk_Setup.exe"
                    chat_id = message["1"]["2"].split('@')[0]
                    send_user_id = message["1"]["10"]["senderUserId"]
                    print("**"**10)
                    print("发送todesk下载地址：")
                    await self.send_msg(websocket, chat_id, send_user_id, msg_todesk)
                    print("**" ** 10)
                    #await self.send_msg(websocket, chat_id, send_user_id, bot_reply)
                    return
            except:
                print("非订单消息,需要自行编写付款后的逻辑")
                pass

            # 判断消息类型
            if self.is_typing_status(message):
                logger.debug("用户正在输入")
                engine.say("用户正在输入")
                engine.runAndWait()
                return
            elif not self.is_chat_message(message):
                logger.debug("其他非聊天消息")
                logger.debug(f"原始消息: {message}")
                return

            # 处理聊天消息
            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]

            # 时效性验证（过滤5分钟前消息）
            if (time.time() * 1000 - create_time) > self.message_expire_time:
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
            if send_user_id == self.myid:
                logger.debug("检测到卖家消息，检查是否为控制命令")

                # 检查切换命令
                if self.check_toggle_keywords(send_message):
                    mode = self.toggle_manual_mode(chat_id)
                    if mode == "manual":
                        logger.info(f"🔴 已接管会话 {chat_id} (商品: {item_id})")
                    else:
                        logger.info(f"🟢 已恢复会话 {chat_id} 的自动回复 (商品: {item_id})")
                    return

                # 记录卖家人工回复
                self.context_manager.add_message_by_chat(chat_id, self.myid, item_id, "assistant", send_message)
                logger.info(f"卖家人工回复 (会话: {chat_id}, 商品: {item_id}): {send_message}")
                return

            #logger.info(f"用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}, 消息: {send_message}")


            print("**"*10)
            database_path = 'data/chat_history.db'  # 指定数据库路径

            if not check_user_exists_in_messages(database_path, send_user_id) and send_message !="发来一条新消息" and send_message!="快给ta一个评价吧～":
                #await self.send_msg(websocket, chat_id, send_user_id, bot_reply)

                print(not check_user_exists_in_messages(database_path, send_user_id),  send_message !="发来一条新消息" , send_message!="快给ta一个评价吧～" )

                
                
                ini_msg  = "您好，老板"

                #msg_list_2_expanded

                for i in msg_list_2_expanded:
                    if i in send_message:
                        bot_reply = "目前是进行到哪一步卡住了？方便的话截图或录个短视频，方便定位问题"
                        ini_msg = bot_reply
                        break

                for i in msg_list_expanded:
                    if i in send_message:
                        bot_reply = "您好，请大概描述下您遇到的问题，方便发下截图吗？视频也行"
                        ini_msg = bot_reply
                        # await self.send_msg(websocket, chat_id, send_user_id, bot_reply)
                        break
                await self.send_msg(websocket, chat_id, send_user_id, ini_msg)
                #其他输入：你好老板



                content = f"您收到一条新顾客消息：{send_message}"
                send_email_notification(subject, content, sender, recver, password)
                msg = "您收到一条新顾客消息：{}".format(send_message)
                print(msg)
                engine.say("新顾客消息")
                engine.runAndWait()
                process_and_print_message_info(message)


            
            print("用户：")
            print(f"用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}, 消息: {send_message}")
            print("**" * 10)


            if("我已付款，等待你发货" in send_message):
                msg_todesk = r"你好，todesk 下载地址：https://dl.todesk.com/windows/ToDesk_Setup.exe"
                await self.send_msg(websocket, chat_id, send_user_id, msg_todesk)
            #[买家确认收货，交易成功]
            #快给ta一个评价吧～
            if("买家确认收货，交易成功" in send_message) or "#快给ta一个评价吧～" in send_message:
                msg_todesk = r"可以的话 辛苦带图好评，谢谢支持"
                await self.send_msg(websocket, chat_id, send_user_id, msg_todesk)
                await asyncio.sleep(2)  # Sleep for 2 seconds



            # 添加用户消息到上下文
            self.context_manager.add_message_by_chat(chat_id, send_user_id, item_id, "user", send_message)

            # 如果当前会话处于人工接管模式，不进行自动回复
            if self.is_manual_mode(chat_id):
                logger.info(f"🔴 会话 {chat_id} 处于人工接管模式，跳过自动回复")
                return
            if self.is_system_message(message):
                logger.debug("系统消息，跳过处理")
                return
            # 从数据库中获取商品信息，如果不存在则从API获取并保存
            item_info = self.context_manager.get_item_info(item_id)
            if not item_info:
                logger.info(f"从API获取商品信息: {item_id}")
                api_result = self.xianyu.get_item_info(item_id)
                if 'data' in api_result and 'itemDO' in api_result['data']:
                    item_info = api_result['data']['itemDO']
                    # 保存商品信息到数据库
                    self.context_manager.save_item_info(item_id, item_info)
                else:
                    logger.warning(f"获取商品信息失败: {api_result}")
                    return
            else:
                logger.info(f"从数据库获取商品信息: {item_id}")

            item_description = f"{item_info['desc']};当前商品售卖价格为:{str(item_info['soldPrice'])}"

            # 获取完整的对话上下文
            context = self.context_manager.get_context_by_chat(chat_id)
            # 生成回复
            bot_reply = self.bot.generate_reply(
                send_message,
                item_description,
                context=context
            )

            # 检查是否为价格意图，如果是则增加议价次数
            if self.bot.last_intent == "price":
                self.context_manager.increment_bargain_count_by_chat(chat_id)
                bargain_count = self.context_manager.get_bargain_count_by_chat(chat_id)
                logger.info(f"用户 {send_user_name} 对商品 {item_id} 的议价次数: {bargain_count}")

            # 添加机器人回复到上下文
            self.context_manager.add_message_by_chat(chat_id, self.myid, item_id, "assistant", bot_reply)

            #logger.info(f"机器人回复: {bot_reply}")


            print("**"*10)
            print("机器人回复:")
            print(bot_reply)
            print("**" * 10)


            #await self.send_msg(websocket, chat_id, send_user_id, bot_reply)



        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")
            logger.debug(f"原始消息: {message_data}")



    async def send_heartbeat(self, ws):
        """发送心跳包并等待响应"""
        try:
            heartbeat_mid = generate_mid()
            heartbeat_msg = {
                "lwp": "/!",
                "headers": {
                    "mid": heartbeat_mid
                }
            }
            await ws.send(json.dumps(heartbeat_msg))
            self.last_heartbeat_time = time.time()
            logger.debug("心跳包已发送")
            return heartbeat_mid
        except Exception as e:
            logger.error(f"发送心跳包失败: {e}")
            raise

    async def heartbeat_loop(self, ws):
        """心跳维护循环"""
        while True:
            try:
                current_time = time.time()

                # 检查是否需要发送心跳
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)

                # 检查上次心跳响应时间，如果超时则认为连接已断开
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break

                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break

    async def handle_heartbeat_response(self, message_data):
        """处理心跳响应"""
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False

    async def main(self):
        # 启动消息队列系统
        await self.message_queue.start()
        logger.info("消息队列系统已启动")
        
        while True:
            try:
                # 重置连接重启标志
                self.connection_restart_flag = False

                headers = {
                    "Cookie": self.cookies_str,
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }

                async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
                    self.ws = websocket
                    await self.init(websocket)

                    # 初始化心跳时间
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()

                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))

                    # 启动token刷新任务
                    self.token_refresh_task = asyncio.create_task(self.token_refresh_loop())

                    # 启动队列统计任务
                    self.stats_task = asyncio.create_task(self._stats_loop())

                    async for message in websocket:
                        try:
                            # 检查是否需要重启连接
                            if self.connection_restart_flag:
                                logger.info("检测到连接重启标志，准备重新建立连接...")
                                break

                            message_data = json.loads(message)
                            print("**"*10)
                            print("原始消息：")
                            if(len(str(message_data))<13519):
                                print(message_data)
                            else:
                                print("原始消息消息太长")
                            print("**" * 10)

                            # 将消息放入队列（生产者）
                            success = await self.message_queue.put_message(message_data, websocket)
                            if not success:
                                logger.warning("消息入队失败，将直接处理")
                                # 如果入队失败，回退到直接处理
                                await self._fallback_message_handler(message_data, websocket)

                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")
                            logger.debug(f"原始消息: {message}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")

            except Exception as e:
                logger.error(f"连接发生错误: {e}")

            finally:
                # 清理任务
                if hasattr(self, 'stats_task') and self.stats_task:
                    self.stats_task.cancel()
                    try:
                        await self.stats_task
                    except asyncio.CancelledError:
                        pass

                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass

                if self.token_refresh_task:
                    self.token_refresh_task.cancel()
                    try:
                        await self.token_refresh_task
                    except asyncio.CancelledError:
                        pass

                # 如果是主动重启，立即重连；否则等待5秒
                if self.connection_restart_flag:
                    logger.info("主动重启连接，立即重连...")
                else:
                    logger.info("等待5秒后重连...")
                    await asyncio.sleep(5)

    async def _fallback_message_handler(self, message_data, websocket):
        """回退的消息处理器，当队列系统失败时使用"""
        try:
            # 处理心跳响应
            if await self.handle_heartbeat_response(message_data):
                return

            # 发送通用ACK响应
            if "headers" in message_data and "mid" in message_data["headers"]:
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": message_data["headers"]["mid"],
                        "sid": message_data["headers"].get("sid", "")
                    }
                }
                # 复制其他可能的header字段
                for key in ["app-key", "ua", "dt"]:
                    if key in message_data["headers"]:
                        ack["headers"][key] = message_data["headers"][key]
                await websocket.send(json.dumps(ack))

            # 记录回退处理的消息
            logger.warning(f"回退处理消息，但不进行详细处理: {type(message_data)}")
            
        except Exception as e:
            logger.error(f"回退消息处理失败: {e}")

    async def _stats_loop(self):
        """队列统计循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒打印一次统计
                stats = self.message_queue.get_stats()
                if stats['total_received'] > 0:
                    logger.info(
                        f"队列统计 - 已接收: {stats['total_received']}, "
                        f"已处理: {stats['total_processed']}, "
                        f"失败: {stats['total_failed']}, "
                        f"队列大小: {stats['queue_size']}, "
                        f"平均处理时间: {stats['processing_time_avg']:.3f}s"
                    )
            except Exception as e:
                logger.error(f"统计循环出错: {e}")
                await asyncio.sleep(30)


if __name__ == '__main__':
    # 加载环境变量
    load_dotenv()

    # 配置日志级别
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    logger.remove()  # 移除默认handler
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.info(f"日志级别设置为: {log_level}")

    cookies_str = os.getenv("COOKIES_STR")
    bot = XianyuReplyBot()
    xianyuLive = XianyuLive(cookies_str)

    print("**"*10)
    print(xianyuLive)
    print(dir(xianyuLive))
    print("**"*10)

    try:
        # 常驻进程
        asyncio.run(xianyuLive.main())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭程序...")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
    finally:
        # 确保消息队列正确关闭
        try:
            asyncio.run(xianyuLive.message_queue.stop())
            logger.info("消息队列已关闭")
        except Exception as e:
            logger.error(f"关闭消息队列时出错: {e}")
        logger.info("程序已退出")
