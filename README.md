# ACM Bot

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-QQ-green.svg)

**专为 ACM/ICPC 竞赛团队及算法爱好者打造的 QQ 机器人**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [指令列表](#-指令列表) • [项目结构](#-项目结构) • [许可证](#-许可证)

---

ACM Bot 为算法竞赛选手提供便捷的信息查询和辅助工具。集成了多平台比赛查询、用户信息追踪、排行榜生成以及 AI 智能问答等功能

## 功能特性

### 竞赛辅助

- **多平台比赛查询**: 一键查询 **Codeforces**、**牛客 (Nowcoder)**、**洛谷 (Luogu)** 以及 **SCPC (西南科技大学校赛平台)** 的近期赛事信息。
- **智能比赛提醒**: 支持群组开启/关闭比赛自动提醒功能，每半小时自动检查并播报即将开始的比赛，不再错过任何一场较量。
- **题目更新推送**: 实时获取 SCPC 平台近期更新的题目，第一时间掌握训练动态。

### 数据可视化

- **用户信息卡片**:
  - **Codeforces**: 生成包含 Rating、Rank、头像等详细信息的用户卡片。
  - **Codeforces**: 绘制用户 Rating 历史变化折线图，直观展示进步曲线。
  - **SCPC**: 查询平台用户信息。

### AI 智能助手

- 内置基于 **Deepseek** 的 AI 助手，支持回答算法竞赛相关问题。
- _注：需在配置文件中配置 Deepseek API Key。_

## 快速开始

### 1. 环境准备

确保已安装 Python 3.8+。

```bash
# 克隆项目到本地
git clone https://github.com/TeAnli/acm-bot
cd acm-bot

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核 (用于图片渲染)
playwright install chromium
```

> [!IMPORTANT]
>
> - **浏览器内核**: 图片生成功能依赖 `Playwright`，请确保 服务器/本地环境已正确安装浏览器内核。
> - **文件权限**: Excel 生成功能需要写入权限，请确保运行目录可写。

### 2. 配置文件

首次运行后，`ncatbot` 会生成配置文件。请在 `data/ACM.yaml` 中添加以下配置以启用 AI 功能：

```yaml
deepseek_api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx" # 你的 Deepseek API Key
ai_system_prompt: "..." # (可选) 自定义 AI 系统提示词
ai_temperature: 0.5 # (可选) AI 温度参数
ai_max_tokens: 800 # (可选) AI 回复最大长度
```

### 3. 运行机器人

```bash
python main.py
```

## 指令列表

### 用户指令

| 指令                | 描述                     | 示例                 |
| :------------------ | :----------------------- | :------------------- |
| `/help`             | 获取帮助信息菜单         | `/help`              |
| `/cf比赛`           | 获取 Codeforces 近期比赛 | `/cf比赛`            |
| `/cf用户 [handle]`  | 获取 CF 用户信息卡片     | `/cf用户 tourist`    |
| `/cf分数 [handle]`  | 获取 CF Rating 折线图    | `/cf分数 jiangly`    |
| `/牛客比赛`         | 获取牛客近期比赛         | `/牛客比赛`          |
| `/洛谷比赛`         | 获取洛谷近期比赛         | `/洛谷比赛`          |
| `/scpc近期比赛`     | 获取 SCPC 平台近期比赛   | `/scpc近期比赛`      |
| `/scpc用户 [name]`  | 获取 SCPC 用户信息       | `/scpc用户 player1`  |
| `/scpc排行`         | 获取 SCPC 本周排行榜     | `/scpc排行`          |
| `/scpc近期更新题目` | 获取近期 SCPC 更新题目   | `/scpc近期更新题目`  |
| `/ai [问题]`        | 向 AI 助手提问           | `/ai 什么是线段树？` |
| `/来个男神`         | 随机发送一张男神照片     | `/来个男神`          |

### 管理员指令

| 指令                 | 描述                      | 示例                 |
| :------------------- | :------------------------ | :------------------- |
| `/开启比赛提醒`      | 开启本群比赛提醒任务      | `/开启比赛提醒`      |
| `/关闭比赛提醒`      | 关闭本群比赛提醒任务      | `/关闭比赛提醒`      |
| `/scpc比赛排行 [id]` | 导出 SCPC 比赛 Excel 榜单 | `/scpc比赛排行 1001` |

## 贡献

你可以提出建议, 或者为本仓库贡献代码.

## 致谢

感谢 [Visual Studio Code](https://code.visualstudio.com/) 提供的强大编辑器支持。
