import time
import os
import json
import re
import random

import requests

# 智能环境配置：仅在未设置时才应用默认值
# 这样兼容 GitHub Actions 的 xvfb-run (会自动设置 DISPLAY) 和 Docker 环境
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"
    
if "XAUTHORITY" not in os.environ:
    # 仅当路径存在时才设置，避免在 GitHub Runner (home/runner) 中报错
    if os.path.exists("/home/headless/.Xauthority"):
        os.environ["XAUTHORITY"] = "/home/headless/.Xauthority"

print(f"[DEBUG] Env DISPLAY: {os.environ.get('DISPLAY')}")
print(f"[DEBUG] Env XAUTHORITY: {os.environ.get('XAUTHORITY')}")

from seleniumbase import SB

# ================= 配置区域 =================
# 代理配置
PROXY_URL = os.getenv("PROXY", "")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# 目标 URL
URL_APP_PANEL = "https://justrunmy.app/panel/application/1935"

# 凭证文件路径
COOKIE_FILE = "cookie.txt"
# ===========================================

class JustRenewal:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(self.BASE_DIR, "artifacts")
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] [INFO] {msg}", flush=True)

    def human_wait(self, min_s=2, max_s=4):
        """随机模拟人类等待时间"""
        time.sleep(random.uniform(min_s, max_s))

    def move_mouse_human(self, sb):
        """模拟人类鼠标晃动预热"""
        try:
            # 在页面不同位置“晃悠”一下鼠标，打破机器人直线模式
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                sb.slow_click(f"body", force=True) # 借用 slow_click 的移动特性，或者直接用 move_to
                time.sleep(random.uniform(0.5, 1.2))
        except: pass

    def get_remaining_time(self, sb, wait=True):
        """获取页面显示的剩余时间 (全面扫描页面文本)"""
        for _ in range(3 if wait else 1): 
            try:
                page_text = sb.get_text("body")
                
                # 匹配带天数的: "2 days 23:20"
                match_days = re.search(r'(\d+)\s*days?\s*(\d{1,2}):(\d{2})', page_text, re.IGNORECASE)
                if match_days:
                    days_str = f"{match_days.group(1)} days {match_days.group(2)}:{match_days.group(3)}"
                    days = int(match_days.group(1))
                    hours = int(match_days.group(2))
                    mins = int(match_days.group(3))
                    return days_str, (days * 1440 + hours * 60 + mins)
                
                # 匹配只有时间的: "23:54"
                match_time = re.search(r'(\d{1,2}):(\d{2})', page_text)
                if match_time:
                    time_str = match_time.group(0)
                    hours = int(match_time.group(1))
                    mins = int(match_time.group(2))
                    return time_str, (hours * 60 + mins)
                
                if not wait: break
                self.log("⏳ 等待数据加载 (拟人化重试)...")
                self.human_wait(3, 5)
            except:
                if not wait: break
                time.sleep(1)
                
        return "Unknown", None

    def save_new_cookie(self, sb):
        """提取并保存更新后的 Cookie"""
        try:
            target_name = '.AspNetCore.Identity.Application'
            all_cookies = sb.get_cookies()
            matching_cookies = [c for c in all_cookies if target_name in c['name'] or c['name'] in target_name]
            
            if not matching_cookies: return

            cookie = max(matching_cookies, key=lambda x: len(x['value']))
            new_value = cookie['value']
            
            old_value = ""
            if COOKIE_FILE and os.path.exists(COOKIE_FILE):
                with open(COOKIE_FILE, 'r') as f:
                    old_value = f.read().strip()
            
            if new_value != old_value and COOKIE_FILE:
                self.log(f"💾 Cookie 状态变更，已自动同步持久化。")
                with open(COOKIE_FILE, 'w') as f:
                    f.write(new_value)
        except: pass

    def send_telegram_notify(self, message, photo_path=None):
        """发送 Telegram 通知 (带图片)"""
        if not TG_TOKEN or not TG_CHAT_ID:
            self.log("⚠️ 未配置 TG_TOKEN 或 TG_CHAT_ID，跳过推送。")
            return
        
        try:
            if photo_path and os.path.exists(photo_path):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as f:
                    # caption 参数用于发送带文字的图片
                    requests.post(url, data={'chat_id': TG_CHAT_ID, 'caption': message}, files={'photo': f})
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={'chat_id': TG_CHAT_ID, 'text': message})
            
            self.log("✅ TG 推送已发送")
        except Exception as e:
            self.log(f"❌ TG 推送失败: {e}")

    def run(self):
        self.log("=" * 40)
        self.log("🚀 JUST RUN MY APP - 拟人化重置流程")
        self.log("=" * 40)

        if not os.path.exists(COOKIE_FILE):
            self.log(f"❌ 错误：找不到凭证文件 {COOKIE_FILE}")
            return

        with open(COOKIE_FILE, 'r') as f:
            cookie_value = f.read().strip()

        self.log("🎯 正在启动 Chrome 浏览器...")
        
        # 使用 headed=True 强制有头模式渲染到 VNC
        with SB(
            uc=True,            # 启用反检测模式
            test=True, 
            headed=True,        # 关键：强制有头模式
            headless=False,     # 明确禁用 headless
            xvfb=False,         # 禁用内部虚拟显示器，使用系统 DISPLAY
            chromium_arg="--no-sandbox,--disable-dev-shm-usage,--disable-gpu,--window-position=0,0,--start-maximized",
            proxy=PROXY_URL if PROXY_URL else None
        ) as sb:
            try:
                self.log("✅ 浏览器已启动！")
                
                # ... (省略中间步骤，保持原有逻辑不变) ...
                
                # 1. IP 检测
                self.log("🌍 正在检测出口 IP...")
                try:
                    sb.open("https://api.ipify.org?format=json")
                    ip_val = json.loads(re.search(r'\{.*\}', sb.get_text("body")).group(0)).get('ip', 'Unknown')
                    parts = ip_val.split('.')
                    self.log(f"✅ 当前出口 IP: {parts[0]}.{parts[1]}.***.{parts[-1]}")
                except:
                    self.log("⚠️ IP 检测跳过...")

                # 2. 访问主页并注入 Cookie
                self.log("🔗 正在访问入口页面...")
                sb.uc_open_with_reconnect("https://justrunmy.app/404", reconnect_time=5)
                self.log("⏳ 等待页面 JS 渲染...")
                time.sleep(10)
                
                sb.add_cookie({
                    'name': '.AspNetCore.Identity.Application',
                    'value': cookie_value,
                    'domain': 'justrunmy.app',
                    'path': '/',
                    'httpOnly': True,
                    'secure': True
                })
                self.log("✅ Cookie 注入成功！")

                # 3. 进入管理面板
                self.log(f"📂 正在进入管理面板...")
                sb.uc_open_with_reconnect(URL_APP_PANEL, reconnect_time=5)
                self.human_wait(5, 8)
                
                if "login" in sb.get_current_url().lower():
                    self.log(f"❌ 权限失效。当前 URL: {sb.get_current_url()}")
                    # ... 省略登录失败处理 ...
                    sb.save_screenshot(f"{self.screenshot_dir}/login_fail.png")
                    self.log(f"📸 失败截图已保存至: {self.screenshot_dir}/login_fail.png")
                    return

                time_str_before, time_before = self.get_remaining_time(sb, wait=True)
                self.log(f"🕒 当前状态: {time_str_before}")

                # 4. 触发弹窗
                self.log("🖱️ 正在点击 'Reset Timer'...")
                self.move_mouse_human(sb)
                sb.click("//button[contains(., 'Reset Timer')]")
                self.human_wait(3, 5)

                # 5. 验证码处理循环 (已优化)
                max_retry_rounds = 3
                for round_idx in range(max_retry_rounds):
                    self.log(f"🔄 执行第 {round_idx + 1}/{max_retry_rounds} 轮验证...")
                    
                    for attempt in range(4):
                        if sb.is_text_visible("Connection lost"):
                            # ... 连接丢失处理 ...
                            try: sb.click("//button[contains(., 'Reload')]")
                            except: sb.refresh()
                            time.sleep(8)
                            continue

                        text_all = sb.get_text("body").lower()
                        has_cf = ("verify you are human" in text_all or 
                                  "challenges.cloudflare" in text_all or
                                  sb.is_element_present('iframe[src*="cloudflare"]') or
                                  sb.is_element_present('iframe[src*="turnstile"]'))
                        has_err = "complete the captcha" in text_all
                        
                        if has_cf or has_err:
                            self.log(f"🛡️ 发现验证挑战 (尝试 {attempt+1})...")
                            sb.save_screenshot(f"{self.screenshot_dir}/captcha_found.png")
                            
                            self.log("⏳ 等待验证码完全加载 (4秒)...")
                            self.human_wait(3, 5)
                            
                            try:
                                self.log("🖱️ 正在尝试点击验证码 (uc_gui_click_captcha)...")
                                sb.uc_gui_click_captcha()
                                self.log("✅ 点击动作已执行")
                            except Exception as e_cap:
                                self.log(f"⚠️ 验证码点击失败: {e_cap}")
                                sb.save_screenshot(f"{self.screenshot_dir}/click_fail.png")

                            self.log("⏳ GUI 点击完成，等待生效 (8秒)...")
                            time.sleep(8)
                            
                            self.log("✅ 动作已执行，准备尝试提交...")
                            break
                        else:
                            self.log("✅ 未发现活跃验证码，准备提交。")
                            break
                    
                    # B. 尝试提交
                    self.log("🖱️ 尝试点击 'Just Reset'...")
                    try:
                        reset_btn = "//button[contains(., 'Just Reset')]"
                        if sb.is_element_visible(reset_btn):
                            sb.click(reset_btn)
                            self.log("✅ 点击指令已发送。")
                            
                            self.log("👀 正在核实提交结果 (3秒)...")
                            time.sleep(3)
                            
                            text_feedback = sb.get_text("body").lower()
                            is_failed = "complete the captcha" in text_feedback
                            is_btn_there = sb.is_element_visible(reset_btn)
                            
                            if is_failed:
                                self.log("❌ 提交被拒：检测到红字报错，需重试验证码。")
                                sb.save_screenshot(f"{self.screenshot_dir}/submit_fail_{round_idx}.png")
                                continue 
                            elif is_btn_there:
                                self.log("⚠️ 按钮仍存在，可能点击未被响应，重试...")
                                continue
                            else:
                                self.log("🎉 按钮已消失，提交判定成功！")
                                break 
                        else:
                            self.log("⚠️ 找不到 'Just Reset' 按钮，可能已自动提交？")
                            break
                    except Exception as e:
                        self.log(f"⚠️ 点击异常: {e}")
                        break
                
                # 6. 审计结果
                self.log("⏳ 等待服务器同步 (15秒)...")
                time.sleep(15)
                time_str_after, time_after = self.get_remaining_time(sb, wait=False)
                self.log(f"🕒 操作后状态: {time_str_after}")

                success = (time_after is not None) and (time_after >= 4318 or (time_before and time_after > time_before))
                
                # 保存最终截图
                final_screenshot = f"{self.screenshot_dir}/final_success.png"
                sb.save_screenshot(final_screenshot)

                if success:
                    self.log("🎉 判定[成功]: 计时器已复位！")
                    self.save_new_cookie(sb)
                    
                    # 发送 TG 通知
                    msg = f"✅ <b>JustRunMy 续期成功</b>\n\n🕒 <b>当前余量:</b> {time_str_after}\n🌍 <b>服务器机房:</b> Docker/Action"
                    self.send_telegram_notify(msg, final_screenshot)
                else:
                    self.log(f"⚠️ 判定[失败]: 数值未见增长。")
                    sb.save_screenshot(f"{self.screenshot_dir}/fail.png")

                self.save_new_cookie(sb)
            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                import traceback
                traceback.print_exc()
                sb.save_screenshot(f"{self.screenshot_dir}/error.png")


if __name__ == "__main__":
    JustRenewal().run()
