import os
import sys
import time
import json
import argparse
import platform
from pathlib import Path
from seleniumbase import SB

def setup_display():
    """设置Linux虚拟显示"""
    if platform.system() == "Linux" and not os.environ.get("DISPLAY"):
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=False, size=(1920, 1080))
            display.start()
            os.environ["DISPLAY"] = display.new_display_var
            print("[*] Linux: Auto-started virtual display (Xvfb)")
            return display
        except ImportError:
            # Assumes environment is already set up or Xvfb is running
            pass
    return None

def bypass_service(url, output_file, proxy=None):
    print(f"[*] Bypass Service Started for: {url}")
    print(f"[*] Output File: {output_file}")
    
    display = setup_display()
    
    try:
        # Use SB context manager. uc=True enables Undetected Mode.
        # headless=False is often required for UC mode to pass, 
        # but Xvfb (virtual display) handles the "headless" part on Linux server.
        with SB(uc=True, test=True, locale="en", proxy=proxy, headless=False) as sb:
            print("[*] Browser launched, loading page...")
            
            sb.uc_open_with_reconnect(url, reconnect_time=4.0)
            
            # Simple check for simple challenges
            if sb.is_element_visible('iframe[src*="challenge"]', timeout=5):
                print("[*] Detected Challenge iframe, attempting GUI click...")
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(2)
                except:
                    pass
            
            time.sleep(4) # Wait for redirects/challenges to clear
            
            # Capture cookies
            cookies = sb.get_cookies()
            ua = sb.execute_script("return navigator.userAgent")
            
            # Check success (cf_clearance usually indicates success)
            cf_clearance = next((c for c in cookies if c['name'] == 'cf_clearance'), None)
            
            if cf_clearance:
                print(f"[+] Success! Got cf_clearance.")
            else:
                print(f"[!] Warning: cf_clearance not found. Might still work if not required.")
                
            # Save to file
            result = {
                "url": url,
                "cookies": {c['name']: c['value'] for c in cookies},
                "user_agent": ua,
                "timestamp": time.time()
            }
            
            with open(output_file, 'w') as f:
                json.dump(result, f)
                
            print(f"[+] Cookies saved to {output_file}")
            
    except Exception as e:
        print(f"[-] Bypass Failed: {e}")
        sys.exit(1)
    finally:
        if display:
            try: display.stop()
            except: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output_file")
    parser.add_argument("--proxy", default=None)
    args = parser.parse_args()
    
    bypass_service(args.url, args.output_file, args.proxy)
