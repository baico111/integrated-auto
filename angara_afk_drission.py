from DrissionPage import ChromiumPage, ChromiumOptions
import time
import random
import sys
import os

# ================= 配置区域 =================
# 填入你的登录信息
USERNAME = "wedukoge@outlook.com"
PASSWORD = "ba%Ph%4f!VsO"
TARGET_URL = "https://freedash.worldofangara.fun/earn/afk"
LOGIN_URL = "https://freedash.worldofangara.fun/login"

# 是否使用无头模式 (VPS 运行建议 True，若想穿透力最强可在此处尝试由我后面提供的 Docker VNC 环境)
HEADLESS = True 
# ===========================================

def log(msg):
    timestamp = time.strftime('%H:%M:%S')
    print(f"[{timestamp}] 🚀 {msg}", flush=True)

def init_page():
    log("正在注魔：启动 v3.0 终极强攻环境...")
    co = ChromiumOptions()
    
    # --- 1. 深度隐藏：抹除所有自动化痕迹 ---
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-setuid-sandbox') 
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--remote-allow-origins=*')
    
    # 核心：彻底禁用自动化标记 (防检测核心)
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    co.set_argument('--no-first-run')
    co.set_argument('--no-default-browser-check')
    
    # 各种反指纹采集伪装气泡
    co.set_argument('--disable-background-networking')
    co.set_argument('--disable-client-side-phishing-detection')
    co.set_argument('--disable-default-apps')
    co.set_argument('--disable-sync')
    co.set_argument('--metrics-recording-only')
    
    # 伪装分辨率与设备像素比
    res_list = ["1920,1080", "1366,768", "1440,900"]
    co.set_argument(f'--window-size={random.choice(res_list)}')
    
    # 伪装 User-Agent (使用真实的最新 Chrome)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    co.set_argument(f'--user-agent={ua}')

    if HEADLESS:
        co.headless(True)
    
    # 路径自适应
    chrome_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium'
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            co.set_browser_path(path)
            break
            
    # 持久化 Profile (热启动，增加信任权重)
    user_data = os.path.abspath('./v3_profile')
    co.set_user_data_path(user_data)
    
    try:
        page = ChromiumPage(co)
        # 注入额外的 stealth 脚本 (彻底抹除 navigator.webdriver)
        page.run_js('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        log("✅ 终极内核启动成功！")
        return page
    except Exception as e:
        log(f"❌ 启动失败: {e}")
        sys.exit(1)

def human_click(page, ele):
    """拟人化点击：移动 -> 等待 -> 点击"""
    try:
        if ele and ele.rect.size[0] > 0:
            # 随机移动到元素范围内
            page.actions.move_to(ele, offset_x=random.randint(-5, 5), offset_y=random.randint(-5, 5))
            time.sleep(random.uniform(0.5, 1.5))
            page.actions.click()
            return True
    except: pass
    return False

def solve_cloudflare(page):
    """【禁咒层】识别并击穿 Cloudflare 验证"""
    try:
        html = page.html.lower()
        if any(t in html for t in ["checking your browser", "challenges.cloudflare", "verify you are human"]):
            log("🛡️ 检测到高阶防护盾，执行深度破解...")
            
            # 等待 Iframe 渲染
            iframe = page.ele('css:iframe[src*="challenges"]', timeout=10)
            if iframe:
                # 方案 A：直接操作 Actions 拟人点击
                log("🖱️ 尝试物理层模拟点击 (Actions)...")
                page.actions.move_to(iframe).click()
                time.sleep(10)
                
                # 方案 B：如果还不行，尝试探测内部按钮
                try:
                    # 进入 Iframe (如果 Drission 支持) 或 直接点击坐标
                    log("🖱️ 补刀：尝试针对中心区域重复点击...")
                    page.actions.move_to(iframe).click()
                except: pass
                
                log("⏳ 等待盾面破碎 (15秒)...")
                time.sleep(15)
                
                if any(t in page.html.lower() for t in ["checking", "challenges"]):
                    log("🔄 破盾超时，执行刷新重置策略...")
                    page.refresh()
                return True
    except: pass
    return False

def check_login(page):
    """全自动化登录层"""
    if "/login" in page.url or "Login" in page.html:
        email = page.ele('@name=email', timeout=5)
        if email:
            log("🔑 进入登录界面，开始注入凭据...")
            email.input(USERNAME)
            time.sleep(random.uniform(1, 2))
            page.ele('@name=password').input(PASSWORD)
            time.sleep(random.uniform(1, 2))
            
            btn = page.ele('@type=submit') or page.ele('tag:button')
            if btn: human_click(page, btn)
            page.wait.load_start()
            return True
    return False

def patrol(page):
    """核心巡检：挂机状态维持"""
    try:
        if solve_cloudflare(page): return
        if check_login(page): return

        # 挂机页面判定
        if "/earn/afk" in page.url:
            html = page.html.lower()
            if "status: active" in html or "earning coins" in html:
                log("🟢 状态：完美。收益正在翻倍中...")
            else:
                start = page.ele('text:Start AFK', timeout=5) or page.ele('text:Begin AFK', timeout=5)
                if start:
                    log("🟡 状态：Idle。已拟人化开启挂机...")
                    human_click(page, start)
                else:
                    log("⏳ 页面加载中，静观其变...")
        else:
            log("📍 错位，正在强制修正路径...")
            page.get(TARGET_URL)
            page.wait(10, 15)

        # 清除万恶的报错弹窗
        try:
            ok = page.ele('text:OK', timeout=1)
            if ok and ok.rect.size[0] > 0:
                log("💥 捕获到 Session 错误，已自动粉碎！")
                human_click(page, ok)
                page.refresh()
        except: pass

    except Exception as e:
        log(f"⚠️ 巡检微波: {e}")

def main():
    log("="*40)
    log(" Angara AFK VPS 脚本 v3.0 (终极强攻版)")
    log("="*40)
    
    page = init_page()
    log(f"🎯 正在潜入目标: {TARGET_URL}")
    page.get(TARGET_URL)
    
    try:
        while True:
            patrol(page)
            
            # 每隔一段时间微操一下，防止心态失衡
            if random.random() > 0.7:
                page.scroll.down(random.randint(100, 300))
                time.sleep(1)
                page.scroll.up(random.randint(100, 300))

            wait_s = random.randint(45, 65)
            log(f"💤 巡检顺利。深度潜伏中 ({wait_s}s)...")
            time.sleep(wait_s)

    except KeyboardInterrupt:
        log("👋 已手动切断连接。")
    finally:
        if 'page' in locals():
            try: page.quit()
            except: pass

if __name__ == "__main__":
    main()
