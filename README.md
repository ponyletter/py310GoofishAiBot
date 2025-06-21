

# 🚀 闲鱼AI智能客服系统 - 消息队列增强版

<div align="center">
<p>
    <a href="#-系统运行效果"><strong>系统运行效果</strong></a> ·
    <a href="#-快速开始"><strong>快速开始</strong></a> ·
    <a href="#-核心功能详解"><strong>功能详解</strong></a> ·
    <a href="#-未来发展规划"><strong>未来规划</strong></a>
</p>
</div>

基于 **XianyuAutoAgent** 和 **XianYuApis** 的简单升级版本，专为闲鱼平台打造的企业级AI值守解决方案。集成了消息队列处理、智能意图识别、本地AI模型支持和多项核心功能优化。

---

### 📋 项目概述
本项目在原有智能闲鱼客服机器人系统基础上，进行了简单升级和功能增强。

### 🙏 致谢
- 感谢 **@shaxiu** 的 [XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent) 项目提供的核心AI对话框架
- 感谢 **@cv-cat** 的 [XianYuApis](https://github.com/cv-cat/XianYuApis) 项目提供的闲鱼API逆向工程支持

---

### ✨ 核心功能特性

🤖 **智能AI对话系统**
- ✅ **多专家Agent架构** - 技术咨询、价格议价、默认对话等专业化处理
- ✅ **智能意图识别** - 基于关键词匹配 + 正则表达式 + 大模型的三级路由策略
- ✅ **上下文记忆** - 完整的对话历史管理和上下文理解
- ✅ **动态议价策略** - 根据议价轮次调整AI回复策略

🔍 **智能消息处理**
- ✅ **关键词检测系统** - 技术类关键词（参数、规格、型号、连接、对比）自动识别
- ✅ **价格关键词识别** - 议价相关词汇（便宜、价、砍价、少点）智能处理
- ✅ **违禁词过滤** - 自动检测并拦截违规内容（微信、QQ、支付宝、银行卡、线下交易）
- ✅ **消息分类处理** - 区分聊天消息、订单消息、系统消息、输入状态

🔄 **高性能消息队列**
- ✅ **异步消息处理** - 基于 `asyncio` 的高性能异步架构
- ✅ **消息重试机制** - 自动重试失败的消息，支持指数退避算法
- ✅ **死信队列** - 处理重试失败的消息，确保消息不丢失
- ✅ **消息去重** - 防止重复处理相同消息，提升系统稳定性
- ✅ **优雅关闭** - 支持安全的程序关闭和资源清理

🎯 **本地AI模型支持**
- ✅ **Ollama集成** - 完整支持本地部署的Ollama模型服务
- ✅ **模型兼容性** - 支持qwen1.5-1.8b-chat等多种开源模型
- ✅ **OpenAI API兼容** - 无缝切换本地模型和云端API
- ✅ **资源优化** - 针对本地部署优化的推理参数

🔊 **实时交互体验**
- ✅ **语音提醒系统** - 用户输入状态实时语音播报（"用户正在输入"）
- ✅ **多平台语音支持** - 支持Windows SAPI、macOS、Linux等多平台TTS
- ✅ **安全语音处理** - 智能检测语音引擎可用性，避免系统崩溃

📊 **用户信息智能分析**
- ✅ **新客户识别** - 自动识别首次对话的新用户
- ✅ **设备信息展示** - 显示用户设备平台、客户端信息
- ✅ **IP地理位置** - 实时获取用户IP归属地信息（国家、地区、城市、ISP）
- ✅ **网络信息分析** - 展示客户端IP、端口等技术信息

🛡️ **系统安全与稳定性**
- ✅ **人工接管模式** - 支持关键词切换AI/人工模式（默认`。`切换）
- ✅ **消息时效检查** - 自动过滤超过5分钟的过期消息
- ✅ **错误隔离处理** - 单个消息处理失败不影响整体系统运行
- ✅ **完整日志系统** - 详细的消息处理链路日志记录

💾 **数据存储与管理**
- ✅ **SQLite数据库** - 轻量级本地数据库存储
- ✅ **消息历史记录** - 完整的对话历史存储和检索
- ✅ **议价次数统计** - 智能统计每个对话的议价轮次
- ✅ **商品信息缓存** - 商品描述和价格信息本地缓存

---

### 🌟 系统运行效果

**新顾客邮箱提醒**

<p align="center">
  <img src="https://img.picui.cn/free/2025/06/22/6856fd99c3332.png" alt="智能议价与用户信息分析" width="800"/>
</p>
**智能议价与用户信息分析**

<p align="center">
  <img src="https://img.picui.cn/free/2025/06/22/6856fd9a0d197.png" alt="技术问题智能解答" width="800"/>
</p>

---

### 📁 自定义回复

![项目结构图](https://img.picui.cn/free/2025/06/22/6856fd9a8523b.png)

<details>
<summary>点击展开/折叠文本目录结构</summary>

```
├── main.py                   # 主程序入口
├── message_queue.py          # 消息队列核心模块
├── message_handlers.py       # 消息处理器
├── XianyuAgent.py            # AI Agent智能体
├── XianyuApis.py             # 闲鱼API接口
├── context_manager.py        # 上下文管理器
├── utils/
│   └── xianyu_utils.py       # 工具函数
├── prompts/                  # AI提示词配置
│   ├── default_prompt.txt    # 默认对话提示词
│   ├── tech_prompt.txt       # 技术咨询提示词
│   ├── price_prompt.txt      # 价格议价提示词
│   └── classify_prompt.txt   # 意图分类提示词
├── data/
│   └── chat_history.db       # SQLite数据库
├── sql/
│   └── main.sql              # 数据库表结构
├── 01ollama/                 # 本地AI模型配置
│   ├── 01main.py             # Ollama原生API调用
│   └── 02openai.py           # OpenAI兼容API调用
├── output/                   # 输出文件目录
├── images/                   # 图片资源
└── tests/                    # 测试文件
    ├── test_simple.py        # 基础功能测试
    ├── test_ping_command.py  # Ping命令测试
    └── test_message_queue.py # 消息队列测试
```
</details>

---

### 🚀 快速开始

#### 环境要求
- Python 3.10+
- 支持异步操作的环境
- （可选）本地Ollama服务

#### 安装步骤

视频部署教程：https://www.bilibili.com/video/BV1wXN2zwE4Y/

1.  **克隆仓库**
    ```bash
    git clone https://github.com/ponyletter/py310GoofishAiBot
    cd XianyuAutoAgent消息队列
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **配置环境变量**
    创建 `.env` 文件，并根据需要填写以下内容：
    ```env
    # AI模型配置（二选一）
    
    # 选项1：使用本地Ollama
    API_KEY=ollama
    MODEL_BASE_URL=http://localhost:11434/v1
    MODEL_NAME=qiuchen/qwen1.5-1.8b-chat:latest
    
    # 选项2：使用云端API
    # API_KEY=your_openai_api_key
    # MODEL_BASE_URL=https://api.openai.com/v1
    # MODEL_NAME=gpt-3.5-turbo
    
    # 必配配置
    COOKIES_STR=your_xianyu_cookies_here
    
    # 可选配置
    TOGGLE_KEYWORDS=. # 人工接管切换关键词
    ```

4.  **本地AI模型配置（可选）**
    如果使用本地Ollama，请执行以下步骤：
    ```bash
    # 安装Ollama
    curl -fsSL https://ollama.ai/install.sh | sh
    
    # 启动Ollama服务
    ollama serve
    
    # 下载模型
    ollama pull qiuchen/qwen1.5-1.8b-chat:latest
    ```
    *语音提醒核心代码*
    ![Ollama模型拉取](https://img.picui.cn/free/2025/06/22/6856fd9a922f9.png)

5.  **配置提示词**
    根据需要修改 `prompts/` 目录下的提示词文件。

6.  **运行程序**
    ```bash
    python main.py
    ```
    *客户收货自动要好评*
    ![程序启动日志](https://img.picui.cn/free/2025/06/22/6856fd9a6fe1e.png)

---

### 🔧 核心功能详解

#### 智能消息处理流程
用户消息 → 消息队列 → 消息分类 → 意图识别 → 专家路由 → AI处理 → 安全过滤 → 回复发送
  ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ↓
去重检查 &nbsp; 异步处理 &nbsp; 类型检查 &nbsp; 关键词匹配 &nbsp; 上下文管理 &nbsp; 本地推理 &nbsp; 违禁词检测 &nbsp; 语音提醒

#### 意图识别策略
- **技术类优先识别**：`参数`、`规格`、`型号`、`连接`、`对比`等关键词
- **价格类智能匹配**：`便宜`、`价`、`砍价`、`少点`等议价词汇
- **正则表达式补充**：`\d+元`、`能少\d+`等模式匹配
- **大模型兜底分类**：复杂语义的智能理解

#### 安全过滤机制
- **违禁词检测**：`微信`、`QQ`、`支付宝`、`银行卡`、`线下`等平台外交易词汇
- **自动回复替换**：检测到违禁词自动回复`"[安全提醒]请通过平台沟通"`
- **消息时效控制**：超过5分钟的消息自动丢弃

#### 用户信息展示
每个新用户首次对话时，系统会自动在后台日志中展示：
- 发信人ID和昵称
- 会话ID和关联商品ID
- 发送平台和设备信息
- 客户端IP地址和地理位置
- 网络技术信息

---

### 🧪 测试功能

#### 运行测试
```bash
# 基础功能测试
python test_simple.py

# 消息队列测试
python test_message_queue.py

# Ping命令测试
python test_message_queue.py
```
*注意：`Ping`命令测试脚本名应为 `test_ping_command.py`，此处原文有误，已在上方代码块中修正。*

#### Ping命令
在闲鱼对话框中发送 `/ping` 可以检查系统状态，系统会回复 `pong` 确认正常运行。

---

### 📊 性能优化

- **内存优化**：消息队列大小限制，防止内存溢出；自动清理过期消息和上下文；优化数据库连接池管理。
- **并发优化**：异步消息处理，提升并发能力；非阻塞IO操作，减少等待时间；智能连接池管理，优化资源使用。
- **AI推理优化**：本地模型部署，降低API调用成本；动态温度调节，优化回复质量；上下文长度控制，提升推理速度。

---

### 🔮 未来发展规划

- **配置管理升级**
  - [ ] **YAML配置文件** - 统一的配置管理方案
  - [ ] **TXT规则文件** - 可视化的关键词和违禁词管理
  - [ ] **热更新配置** - 无需重启的配置动态加载
- **图片ORC**
  - [ ] 通过`paddleocr`库转文本
- **数据库架构升级**
  - [ ] **MySQL数据库** - 企业级数据库支持
  - [ ] **数据表规范化** - 符合3NF的表结构设计
  - [ ] **分库分表** - 大规模数据的水平扩展
  - [ ] **数据备份策略** - 自动化的数据备份和恢复
- **功能扩展计划**
  - [ ] **Web管理界面** - 可视化的系统管理控制台
  - [ ] **实时监控面板** - 系统状态和性能监控
  - [ ] **消息统计分析** - 详细的对话数据分析
  - [ ] **多账号支持** - 支持多个闲鱼账号同时运行
  - [ ] **分布式架构** - 支持集群部署和负载均衡
- **AI能力提升**
  - [ ] **多模态支持** - 图片识别和语音处理
  - [ ] **知识库集成** - 商品知识库和FAQ系统
  - [ ] **情感分析** - 用户情绪识别和个性化回复
  - [ ] **推荐系统** - 智能商品推荐功能

---

### 🐛 问题修复记录
| 问题描述           |   状态   | 修复方案                         |
| :----------------- | :------: | :------------------------------- |
| 用户消息重复回复   | ✅ 已修复 | 移除重复的AI回复生成逻辑         |
| 语音引擎属性错误   | ✅ 已修复 | 添加安全的语音引擎检查和异常处理 |
| 订单消息类型错误   | ✅ 已修复 | 增强类型检查和安全的数据提取     |
| Ping命令无响应     | ✅ 已修复 | 实现完整的ping-pong响应机制      |
| IP地理位置查询失败 | ✅ 已修复 | 添加API异常处理和降级方案        |
| 消息队列内存泄漏   | ✅ 已修复 | 实现自动清理和内存限制机制       |

---

### 🔧 技术栈
- **后端框架**: Python 3.10+ + AsyncIO
- **AI模型**: OpenAI API / 本地Ollama
- **数据库**: SQLite (计划升级MySQL)
- **消息队列**: 自研异步消息队列
- **语音合成**: pyttsx3 (跨平台TTS)
- **网络通信**: WebSocket + HTTP
- **日志系统**: Loguru
- **配置管理**: python-dotenv

---

### ⚠️ 注意事项
- 本项目仅供学习与交流使用，请遵守相关平台使用条款。
- 使用前请确保已获得必要的授权和许可。
- 建议在测试环境中充分验证后再部署到生产环境。
- 定期备份重要数据，避免数据丢失。

---

### 🤝 贡献指南
欢迎提交Issue和Pull Request来改进项目！

1.  Fork 本仓库
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  开启 Pull Request

---

### 📄 许可证
本项目采用 [GPL-3.0](LICENSE) 许可证。

---

### 📞 联系方式
如有问题或建议，请通过以下方式联系：
- 提交 [Issue](https://github.com/ponyletter/py310GoofishAiBot/issues)
- 发送邮件至 `pony.letter@gmail.com`



<div align="center">
⭐ 如果这个项目对您有帮助，请给我们一个Star！您的支持是我们持续改进的动力！⭐
</div>
