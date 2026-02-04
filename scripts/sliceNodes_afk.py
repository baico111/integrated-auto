import os
import time
import logging
import random
from DrissionPage import ChromiumPage, ChromiumOptions

# 强制设置 X11 环境，确保连接到容器内的 VNC 桌面
os.environ["DISPLAY"] = ":1"
os.environ["XAUTHORITY"] = "/home/headless/.Xauthority"

# ================= 配置区域 =================
LOGIN_URL = "https://dash.slicenodes.in/auth/login"
AFK_URL = "https://dash.slicenodes.in/earn/afk"
USERNAME = "wedukoge@outlook.com"
PASSWORD = "R!pT@O2Xm%KO"
IDLE_TIMEOUT = 300  # 5 分钟无变化则重启 (秒)

LOG_PATH = "afk_monitor.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def run_main_workflow(page):
    """执行核心流程：登录 -> 跳转 -> 点击 AFK 按钮"""
    # 1. 优先尝试访问 AFK 页面 (利用持久化 Session)
    logging.info(f"🔗 正在尝试访问 AFK 页面: {AFK_URL}")
    page.get(AFK_URL)
    time.sleep(3)
    
    if "auth/login" in page.url:
        logging.info("🔑 检测到未登录，正在执行登录流程...")
        username_field = page.ele('#email', timeout=10)
        if not username_field:
            username_field = page.ele('@placeholder*=email or username', timeout=2)
            
        if username_field:
            username_field.clear()
            username_field.input(USERNAME)
            logging.info("✅ 账号已填入")
        
        time.sleep(1)
        password_field = page.ele('@type=password', timeout=5)
        if password_field:
            password_field.clear()
            password_field.input(PASSWORD)
            logging.info("✅ 密码已填入")
        
        logging.info("🛡️ 等待 Cloudflare 验证通过 (最多15秒)...")
        for i in range(15):
            time.sleep(1)
            # 检测验证是否失败
            if page.ele('text:失败', timeout=0.5) or page.ele('text:Verify you are human', timeout=0.5):
                logging.warning("⚠️ Cloudflare 验证失败，刷新页面重试...")
                page.refresh()
                time.sleep(3)
                return False  # 让外层重试
        
        login_btn = page.ele('@@tag():button@@text():Login', timeout=5)
        if not login_btn:
             login_btn = page.ele('t:Login')
             
        if login_btn:
            login_btn.click()
            logging.info("🖱️ 点击登录按钮")
            time.sleep(5)
            
            # 检测登录是否成功
            if "auth/login" in page.url:
                logging.error("❌ 登录失败！仍在登录页面，可能验证码未通过")
                page.get_screenshot(path='logs/login_failed.png')
                return False
            
            logging.info("✅ 登录成功！")
        
        if AFK_URL not in page.url:
            logging.info("✈️ 跳转至挂机页面...")
            page.get(AFK_URL)
            time.sleep(3)
    else:
        logging.info("🎉 已处于登录状态，跳过登录步骤")
    
    # 5. 开启数据监听
    page.listen.start('afk') 
    
    # 6. 环境校准：强制固定大视口，并死等页面加载完成
    page.set.window.size(1920, 1080)
    logging.info("⏳ 正在等待页面完全加载 (包含异步组件)...")
    page.wait.doc_loaded()
    time.sleep(8) # 给 React 组件留出充足的 Hydration 时间
    
    # 提前判定：如果已经 Active，则直接通过
    if page.ele('text:Active', timeout=3):
        logging.info("✅ 页面检测到 Active 标记，挂机已在运行中")
        return True

    for attempt in range(1, 15):
        logging.info(f"🔍 [深度扫描] 正在全页面(含Shadow-root)定位挂机入口 (第 {attempt}/14 次)...")
        
        # 1. 穿透模式：寻找所有可见按钮
        all_eles = page.eles('tag:button')
        
        target_ele = None
        for ele in all_eles:
            try:
                txt = ele.text.strip().lower()
                # 极其宽容的关键字匹配
                if "start" in txt and "afk" in txt:
                    target_ele = ele
                    break
            except:
                continue
        
        # 2. 备选方案：全文本模糊搜索
        if not target_ele:
            target_ele = page.ele('text:Start AFK', timeout=1)
            
        if target_ele:
            logging.info(f"🎯 成功锁定目标！标签: {target_ele.tag}, 显示文本: {target_ele.text.strip()}")
            try:
                # 悬停激活
                target_ele.hover()
                time.sleep(1)
                
                # 物理坐标点击 (之前成功的模式)
                rect = target_ele.rect.click_point
                logging.info(f"📍 准备物理点击: {rect}")
                page.actions.move_to(rect).click()
                logging.info("🖱️ 物理点击已执行")
                time.sleep(5)
                
                # 状态判定
                if page.ele('text:Active', timeout=3):
                    logging.info("✅ 挂机状态已转为 Active！")
                    return True
                
                # JS 兜底
                logging.warning("⚠️ 物理点击未生效，尝试 JS 补刀...")
                page.run_js('arguments[0].click();', target_ele)
                time.sleep(5)
                
                if page.ele('text:Active', timeout=3):
                    logging.info("✅ 状态回检成功：Active (JS成功)")
                    return True
                break
            except Exception as e:
                logging.error(f"❌ 交互异常: {e}")
                break
        
        # 每轮都看一眼是否已经激活
        if page.ele('text:Active', timeout=1):
            logging.info("✅ 发现 Active 标记，任务达成")
            return True
        time.sleep(2)
    
    # 彻底失败：保存源码和截图用于离线分析
    page.get_screenshot(path='logs/final_error.png')
    with open('logs/page_source.html', 'w', encoding='utf-8') as f:
        f.write(page.html)
    logging.error("❌ 无法在当前页面执行点击。已保存 logs/final_error.png 和 logs/page_source.html 请发给助手分析。")
    return False

def start_afk_monitor():
    # 浏览器启动设置
    co = ChromiumOptions()
    
    # 1. 增强浏览器路径探测 (适配多种 Linux 发行版)
    browser_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium"
    ]
    found_path = None
    for bp in browser_paths:
        if os.path.exists(bp):
            found_path = bp
            break
            
    if found_path:
        co.set_browser_path(found_path)
    
    # 2. 极致无头模式 + 反 Cloudflare 检测参数
    co.headless(True)
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--headless=new')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    co.set_argument('--window-size=1920,1080')
    # 伪装真实浏览器 User-Agent
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 3. 动态路径适配 (使用脚本所在目录，防止 Root 运行报错)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_path = os.path.join(base_dir, "browser_data")
    logs_dir = os.path.join(base_dir, "logs")
    
    for d in [user_data_path, logs_dir]:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            
    co.set_user_data_path(user_data_path)
    co.set_local_port(random.randint(9000, 9999)) # 随机端口防止冲突
    co.mute(True)
    
    try:
        page = ChromiumPage(co)
    except Exception as e:
        logging.error(f"❌ 浏览器启动失败! 检查是否缺少依赖 (libnss3, etc). 错误: {e}")
        return
    
    while True: # 外层无限循环实现重启
        try:
            logging.info("🔄 开始新一轮挂机流程...")
            if not run_main_workflow(page):
                logging.warning("⚠️ 挂机流程执行不完全，等待重试...")
                time.sleep(10)
                continue

            logging.info("📡 进入长效监控模式...")
            last_coins = "Unknown"
            last_active_time = time.time()
            
            while True:  # 监控循环
                monitor_start = time.time()
                try:
                    # 方式 A: 监听数据包
                    res = page.listen.wait(timeout=5)
                    if res:
                        logging.info("📊 监听到 API 数据流，刷新活跃时间")
                        last_active_time = time.time()
                    
                    # 方式 B: 读取 DOM 数值
                    coins_ele = page.ele('text:Total Coins', timeout=2)
                    if coins_ele:
                        try:
                            # 鲁棒性防崩：直接找后续文本
                            current_coins = coins_ele.next().text
                            if current_coins != last_coins:
                                logging.info(f"💰 [数值变化] Total Coins: {current_coins}")
                                last_coins = current_coins
                                last_active_time = time.time()
                        except:
                            pass
                    
                    # 检查是否超时
                    idle_duration = time.time() - last_active_time
                    if idle_duration > IDLE_TIMEOUT:
                        logging.error(f"🚨 警告：已连续 {int(idle_duration)} 秒无数值变化，准备重启流程！")
                        break # 跳出监控循环，触发重新登录/跳转
                        
                    # 检查 Status 状态 (额外保底)
                    status_ele = page.ele('text:Status:', timeout=2)
                    if status_ele:
                        try:
                            if "Inactive" in status_ele.next().text:
                                logging.warning("🚨 检测到状态变回 Inactive，尝试重启！")
                                break
                        except:
                            pass

                except Exception as e_inner:
                    logging.debug(f"监控细节波动: {e_inner}")
                
                time.sleep(30) # 每 30 秒轮询一次
                
        except Exception as e_outer:
            logging.error(f"❌ 流程发生全局异常: {e_outer}")
            time.sleep(10) # 冷却后重启

if __name__ == "__main__":
    start_afk_monitor()
