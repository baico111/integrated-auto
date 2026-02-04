#!/bin/bash

# ================= 配置区域 =================
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/sliceNodes_afk.py"
LOG_FILE="$SCRIPT_DIR/afk_monitor.log"
PID_FILE="$SCRIPT_DIR/afk_monitor.pid"
VENV_DIR="$SCRIPT_DIR/.venv"
MAX_LOG_LINES=200

# 切换到脚本目录
cd "$SCRIPT_DIR"

log_info() { echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1"; }
log_warn() { echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $1"; }
log_error() { echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1"; }

# 1. 终极自愈逻辑 (强制安装 Google Chrome)
fix_environment() {
    log_info "正在进行【环境大手术】：强制校准官方浏览器组件..."

    # 1.1 针对 Ubuntu 的极致修复：移除 Snap 版 Chromium 并安装官方 Google Chrome
    if command -v apt-get &> /dev/null; then
        if ! command -v google-chrome &> /dev/null; then
            log_info "检测到环境不稳定，正在强制安装官方 Google Chrome (稳定版)..."
            apt-get update
            apt-get install -y wget gnupg
            # 下载官方 deb 包
            wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
            # 安装并补全依赖
            apt-get install -y ./google-chrome.deb
            rm -f google-chrome.deb
            # 补全基础运行库
            apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
                libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
                libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0
        fi
    elif command -v apk &> /dev/null; then
        # Alpine 环境保持原样
        apk update && apk add chromium nss atk at-spi2-atk mesa-gbm alsa-lib pango cairo
    fi

    # 1.2 清理陈旧的数据文件夹防止权限冲突
    if [ -d "$SCRIPT_DIR/browser_data" ]; then
        log_info "清理历史缓存以防止冲突..."
        rm -rf "$SCRIPT_DIR/browser_data"
    fi

    # 1.3 极简预检：Python 环境
    if [ ! -d "$VENV_DIR" ] || ! "$VENV_DIR/bin/python3" -c "import DrissionPage" &> /dev/null; then
        log_info "正在同步 Python 隔离环境 (venv)..."
        [ -x "$(command -v apt-get)" ] && apt-get install -y python3-venv
        [ -x "$(command -v apk)" ] && apk add py3-venv
        python3 -m venv "$VENV_DIR" --with-pip || python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/python3" -m pip install --no-cache-dir DrissionPage -i https://pypi.tuna.tsinghua.edu.cn/simple
    fi

    touch "$SCRIPT_DIR/.sys_libs_installed"
    log_info "官方环境加固已就绪。"
}

# 2. 深度清理
stop() {
    log_info "正在停止所有相关进程 (强制清理)..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill -9 $PID 2>/dev/null
    fi
    # 清理所有 chromium 和 chrome 进程，防止端口占用
    pkill -9 -f "chromium" 2>/dev/null
    pkill -9 -f "chrome" 2>/dev/null
    pkill -9 -f "$PYTHON_SCRIPT" 2>/dev/null
    pkill -9 -f "tail -f /dev/null" 2>/dev/null
    rm -f "$PID_FILE"
    log_info "清理完成。"
}

# 3. 启动
start() {
    # 每次 start 前强制清理一次
    stop

    fix_environment

    log_info "正在使用官方 Google Chrome 启动挂机程序..."
    PYTHON_EXE="$VENV_DIR/bin/python3"
    [ ! -f "$PYTHON_EXE" ] && PYTHON_EXE="python3"

    # 清空旧日志，避免干扰
    cat /dev/null > "$LOG_FILE"

    nohup "$PYTHON_EXE" "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    log_info "已在后台飞速运行 (PID: $NEW_PID)。"
}

status() {
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null; then
        log_info "运行中 (PID: $(cat "$PID_FILE"))。请看监控实效："
        tail -n 20 "$LOG_FILE"
    else
        log_warn "程序当前未运行。最新日志摘要："
        tail -n 10 "$LOG_FILE"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    restart) stop; start ;;
    *) echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac
