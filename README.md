# 🤖 Automation Integrated (集成版)

[![Build and Push Docker Image](https://github.com/debbide/integrated/actions/workflows/docker-image.yml/badge.svg)](https://github.com/debbide/integrated/actions/workflows/docker-image.yml)
[![Docker Image](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/debbide/integrated/pkgs/container/integrated)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Automation Integrated** 是一个全栈集成的自动化工控平台镜像。它将 **Web 管理后台**、**任务调度引擎**、**桌面环境**、**浏览器环境**以及**远程监控**完美结合，旨在为网页爬虫、RPA 自动化、定时签到等场景提供一站式解决方案。

---

## ✨ 核心能力

### 🖥️ 一站式管理面板 (Web UI)
- **任务可视化**：通过网页直接添加、禁用、手动触发定时任务。
- **集成编辑器**：内置基于 Web 的代码编辑器，支持直接修改 Python 和 AutoKey 脚本。
- **调度系统**：支持标准 Cron 表达式。
- **执行审计**：查看脚本运行状态和控制台输出日志。

### 🤖 强大的自动化驱动
- **SeleniumBase & UC Driver**：预装并锁定兼容 132 版本的 Chrome 与驱动，完美支持绕过 Cloudflare 验证。
- **AutoKey (GTK)**：系统级键盘鼠标模拟，支持复杂的图形算法和坐标点击。
- **多语言脚本**：原生支持 Python、Selenium IDE (.side) 格式脚本。

### 🌐 远程监控与网络
- **noVNC 桌面**：集成无需客户端的远程桌面，可实时查看脚本运行动作。
- **Nginx 反向代理**：统一 8080 端口访问 Web UI 与 VNC。
- **Cloudflare Tunnel**：内置内网穿透功能，只需一个 Token 即可在公网安全管理容器。

### 📦 瘦身与优化
- **Openbox 极简桌面**：极低内存占用（约 100MB 待机），适合低配 VPS 或 PaaS 平台（如 Railway, Zeabur）。
- **多架构构建**：支持 `linux/amd64` 和 `linux/arm64`。

---

## 🛠️ 快速启动

### 使用 Docker Compose (推荐)

创建 `docker-compose.yml`:

```yaml
services:
  automation:
    image: ghcr.io/debbide/integrated:latest
    container_name: automation-integrated
    ports:
      - "8080:8080"
    environment:
      - VNC_RESOLUTION=1360x768
      - TZ=Asia/Shanghai
      - VNC_PW=admin
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=admin123
      - ENABLE_CLOUDFLARE_TUNNEL=false
      - CLOUDFLARE_TUNNEL_TOKEN=
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./Downloads:/home/headless/Downloads
      - ./scripts:/home/headless/.config/autokey/data/MyScripts
    shm_size: '2gb'
    restart: unless-stopped
```

启动命令：
```bash
docker compose up -d
```

访问地址：`http://localhost:8080`

---

## 📖 脚本编写说明

### Cloudflare 绕过示例
在 Python 脚本首行添加 `# BYPASS_URL=...` 标记，系统会自动处理验证：

```python
# BYPASS_URL=https://example.com/checkin
from selenium import webdriver
import os

# 获取系统自动生成的 Cookies 文件路径
cookie_file = os.environ.get('CF_COOKIES_FILE')
# ... 执行登录逻辑
```

### AutoKey 模拟器
AutoKey 脚本存放在 `/home/headless/.config/autokey/data/MyScripts`，可以通过 Web 面板即时保存并执行。

---

## 🏗️ 开发者构建

如果你想自行修改并构建镜像：

```bash
# 本地构建
docker build -t integrated:local .

# 推送到远程 (支持多架构)
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/your-user/integrated:latest --push .
```

---

## 📜 许可证
本项目采用 MIT 许可证。

## Enjoy your automation! 🚀
