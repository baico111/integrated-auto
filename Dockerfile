# ===================================================================
# 基础镜像与环境
# ===================================================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
USER root

# 环境变量
ENV TZ=Asia/Shanghai \
  HOME=/home/headless \
  LANG=zh_CN.UTF-8 \
  LANGUAGE=zh_CN:zh \
  LC_ALL=zh_CN.UTF-8 \
  DATABASE_URL=sqlite:////app/data/tasks.db \
  SQLALCHEMY_DATABASE_URI=sqlite:////app/data/tasks.db \
  SQLALCHEMY_TRACK_MODIFICATIONS=false \
  SCHEDULER_TIMEZONE=Asia/Shanghai \
  SCHEDULER_API_ENABLED=true \
  SCRIPTS_DIR=/home/headless/Downloads \
  MAX_SCRIPT_TIMEOUT=300 \
  RETRY_FAILED_TASKS=true \
  MAX_RETRIES=3 \
  LOG_LEVEL=INFO \
  LOG_FILE=/app/data/automation.log \
  CHROME_BINARY=/usr/bin/google-chrome-stable \
  FLASK_ENV=production \
  FLASK_DEBUG=false \
  HOST=0.0.0.0 \
  PORT=8080 \
  DISPLAY=:1 \
  VNC_PORT=5901 \
  NOVNC_PORT=6901 \
  VNC_RESOLUTION=1360x768 \
  VNC_COL_DEPTH=16 \
  VNC_PW=admin \
  ADMIN_USERNAME=admin \
  ADMIN_PASSWORD=admin123 \
  XDG_CONFIG_DIRS=/etc/xdg \
  XDG_DATA_DIRS=/usr/local/share:/usr/share \
  PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# ===================================================================
# 系统安装 (核心层)
# ===================================================================
# ===================================================================
# 系统安装 (核心层)
# ===================================================================
# 使用阿里云镜像加速 (通常比清华更稳定)
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
  sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list

# 1. 基础依赖与本地化
RUN apt-get update && \
  apt-get install -y --no-install-recommends --fix-missing \
  software-properties-common gpg-agent wget curl ca-certificates git \
  vim nano sudo tzdata locales net-tools openssh-client \
  iproute2 iputils-ping supervisor cron sqlite3 \
  fonts-wqy-microhei language-pack-zh-hans && \
  # 配置语言环境
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
  locale-gen zh_CN.UTF-8 && update-locale LANG=zh_CN.UTF-8 && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. X11 / VNC / Openbox 桌面环境
RUN apt-get update && \
  apt-get install -y --no-install-recommends --fix-missing \
  x11-utils x11-xserver-utils xauth xserver-xorg-core xserver-xorg-video-dummy \
  tigervnc-standalone-server tigervnc-common tigervnc-tools \
  libasound2 openbox tint2 pcmanfm lxterminal dbus-x11 libgtk-3-0 autocutsel && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Python & 开发环境
RUN apt-get update && \
  apt-get install -y --no-install-recommends --fix-missing \
  python3 python3-pip python3-dev python3-gi python3-xdg python3-websockify \
  gir1.2-gtk-3.0 pkg-config gcc g++ make libffi-dev libssl-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Chrome 依赖与自动化工具
RUN apt-get update && \
  apt-get install -y --no-install-recommends --fix-missing \
  xautomation xdotool kdialog imagemagick nginx nodejs npm unzip p7zip-full \
  autokey-gtk \
  libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxrandr2 \
  libpangocairo-1.0-0 libpango-1.0-0 libcups2 libdbus-1-3 libxdamage1 libxfixes3 \
  libgbm1 libdrm2 libwayland-client0 libatspi2.0-0 && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# 5. 浏览器安装 (Multi-Arch - 锁定 132 版本)
RUN if [ "$TARGETARCH" = "amd64" ]; then \
  echo "🔵 Installing Chrome for Testing (132.0.6834.110) for AMD64..."; \
  wget -q "https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.110/linux64/chrome-linux64.zip" -O /tmp/chrome.zip && \
  unzip -q /tmp/chrome.zip -d /opt/ && \
  ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
  rm /tmp/chrome.zip; \
  elif [ "$TARGETARCH" = "arm64" ]; then \
  echo "🟠 Installing Chromium for ARM64..."; \
  apt-get update && apt-get install -y chromium-browser; \
  ln -s /usr/bin/chromium-browser /usr/bin/google-chrome; \
  fi && \
  # 创建包装脚本，避免直接调用导致参数丢失
  echo '#!/bin/bash' > /usr/bin/google-chrome-stable && \
  echo 'exec /usr/bin/google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --no-default-browser-check --no-first-run --disable-extensions --disable-background-networking --disable-sync --disable-translate --disable-software-rasterizer --memory-pressure-off --js-flags="--max-old-space-size=256" "$@"' >> /usr/bin/google-chrome-stable && \
  chmod +x /usr/bin/google-chrome-stable && \
  update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/bin/google-chrome-stable 200 && \
  update-alternatives --set x-www-browser /usr/bin/google-chrome-stable

# 6. Cloudflare Tunnel
RUN echo "Downloading Cloudflared for $TARGETARCH..." && \
  wget -q "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$TARGETARCH.deb" -O cloudflared.deb && \
  dpkg -i cloudflared.deb || (apt-get update && apt-get install -f -y) && \
  rm -f cloudflared.deb

# 7. 用户与权限配置
RUN groupadd -g 1001 headless && \
  useradd -u 1001 -g 1001 -m -s /bin/bash headless && \
  echo "headless ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
  # 瘦身清理 (可选，这里先注释掉，防止清理掉后面需要的依赖)
  # apt-get remove -y --purge gcc g++ make python3-dev software-properties-common gpg-agent && \
  apt-get autoremove -y && \
  rm -rf /usr/share/doc /usr/share/man /usr/share/info && \
  apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ===================================================================
# 配置 Openbox (替代 XFCE)
# ===================================================================
RUN mkdir -p /app/web-app /app/scripts /app/data /app/logs /home/headless/Downloads \
  /home/headless/.config/autokey/data/Sample\ Scripts \
  /home/headless/.config/autokey/data/My\ Phrases \
  /home/headless/.config/autokey/data/MyScripts \
  /home/headless/.config/openbox \
  /home/headless/.config/tint2 \
  /home/headless/.vnc && \
  chown -R headless:headless /app /home/headless

# === 强制 Tint2 任务栏在屏幕顶部 ===
RUN echo 'panel_position = top center horizontal\n\
  panel_size = 100% 30\n\
  panel_layer = top\n\
  panel_items = TSC\n\
  panel_background_id = 1\n\
  wm_menu = 1\n\
  panel_dock = 0\n\
  rounded = 0\n\
  border_width = 0\n\
  background_color = #222222 100\n\
  border_color = #000000 0\n\
  taskbar_mode = single_desktop\n\
  taskbar_padding = 2 2 2\n\
  taskbar_background_id = 0\n\
  taskbar_active_background_id = 1\n\
  systray_padding = 4 2 4\n\
  systray_sort = right2left\n\
  systray_background_id = 0\n\
  systray_icon_size = 20\n\
  time1_format = %H:%M\n\
  time2_format = %A %d %B\n\
  clock_font_color = #eeeeee 100\n\
  clock_padding = 4 2\n\
  clock_background_id = 0' > /home/headless/.config/tint2/tint2rc && \
  chown -R headless:headless /home/headless/.config/tint2

# === 自定义 Openbox 右键菜单 (menu.xml) ===
RUN cat << 'EOF' > /home/headless/.config/openbox/menu.xml
<?xml version="1.0" encoding="UTF-8"?>
<openbox_menu xmlns="http://openbox.org/3.4/menu">
<menu id="root-menu" label="Openbox 3">
<item label="Google Chrome">
<action name="Execute">
<command>google-chrome-stable --no-sandbox</command>
</action>
</item>
<item label="AutoKey">
<action name="Execute">
<command>autokey-gtk --verbose</command>
</action>
</item>
<separator />
<item label="Terminal">
<action name="Execute">
<command>lxterminal</command>
</action>
</item>
<item label="File Manager">
<action name="Execute">
<command>pcmanfm</command>
</action>
</item>
<separator />
<item label="Restart Openbox">
<action name="Restart" />
</item>
</menu>
</openbox_menu>
EOF
RUN chown headless:headless /home/headless/.config/openbox/menu.xml

# === Openbox 配置文件 (rc.xml) - 终端置顶 ===
RUN mkdir -p /home/headless/.config/openbox && \
  cp /etc/xdg/openbox/rc.xml /home/headless/.config/openbox/rc.xml && \
  sed -i 's|</applications>|  <application class="Lxterminal">\n    <layer>above</layer>\n  </application>\n</applications>|' /home/headless/.config/openbox/rc.xml && \
  chown headless:headless /home/headless/.config/openbox/rc.xml

# === 关键修改：Openbox 自动启动脚本 ===
# 移除了 'pcmanfm --desktop'，防止它遮挡 Openbox 的右键菜单
RUN echo 'autocutsel -fork -selection PRIMARY & \n\
  autocutsel -fork -selection CLIPBOARD & \n\
  tint2 & \n\
  /usr/bin/autokey-gtk --verbose &' > /home/headless/.config/openbox/autostart && \
  chown headless:headless /home/headless/.config/openbox/autostart

# VNC 启动脚本
RUN cat << 'EOF' > /home/headless/.vnc/xstartup
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
eval $(dbus-launch --sh-syntax)
export DBUS_SESSION_BUS_ADDRESS
echo "export DBUS_SESSION_BUS_ADDRESS='$DBUS_SESSION_BUS_ADDRESS'" > $HOME/.dbus-env
chmod 644 $HOME/.dbus-env
# 纯色背景 (因为我们去掉了 pcmanfm --desktop，所以需要手动设置背景)
xsetroot -solid "#333333" &
xset s off &
xset -dpms &
xset s noblank &
export GTK_IM_MODULE=xim
export XMODIFIERS=@im=none
export LANG=zh_CN.UTF-8
exec /usr/bin/openbox-session
EOF
RUN chmod +x /home/headless/.vnc/xstartup && chown headless:headless /home/headless/.vnc/xstartup

# ===================================================================
# 安装 noVNC
# ===================================================================
WORKDIR /tmp
RUN mkdir -p /usr/share/novnc && \
  wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz | tar xz --strip-components=1 -C /usr/share/novnc && \
  mkdir -p /usr/share/novnc/utils/websockify && \
  wget -qO- https://github.com/novnc/websockify/archive/refs/tags/v0.11.0.tar.gz | tar xz --strip-components=1 -C /usr/share/novnc/utils/websockify && \
  ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html && \
  chown -R headless:headless /usr/share/novnc && \
  chmod -R 755 /usr/share/novnc

# ===================================================================
# Python 环境
# ===================================================================
COPY web-app/requirements.txt /app/web-app/
RUN pip install --no-cache-dir --upgrade pip setuptools && \
  pip install --no-cache-dir --ignore-installed -r /app/web-app/requirements.txt && \
  rm -rf /root/.cache/pip

# ===================================================================
# 复制与配置
# ===================================================================
COPY web-app/ /app/web-app/
COPY nginx.conf /etc/nginx/nginx.conf
COPY scripts/ /app/scripts/
COPY services.conf /etc/supervisor/conf.d/services.conf
COPY browser-configs/chrome.zip /tmp/chrome.zip

RUN mkdir -p /home/headless/.config/google-chrome && \
  unzip -q /tmp/chrome.zip -d /home/headless/.config/google-chrome/ && \
  rm /tmp/chrome.zip && \
  rm -f /home/headless/.config/google-chrome/SingletonLock && \
  chown -R headless:headless /home/headless/.config

RUN echo '#!/bin/bash' > /usr/local/bin/init-database && \
  echo 'cd /app/web-app && python3 init_db.py' >> /usr/local/bin/init-database && \
  chmod +x /usr/local/bin/init-database

RUN chown -R headless:headless /app /home/headless \
  && chown -R www-data:www-data /var/log/nginx /var/lib/nginx 2>/dev/null || true \
  && chmod +x /app/scripts/*.sh 2>/dev/null || true \
  && mkdir -p /tmp/.X11-unix /tmp/.ICE-unix \
  && chmod 1777 /tmp/.X11-unix /tmp/.ICE-unix

# ===================================================================
# 预装 SeleniumBase UC Driver (物理锁定稳定版)
# ===================================================================
# 使用 132.0.6834.110 稳定版驱动
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.110/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
  unzip /tmp/chromedriver.zip -d /tmp/ && \
  mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
  chmod +x /usr/bin/chromedriver && \
  rm -rf /tmp/chromedriver*

# 2. 物理预装驱动并暴力授权
RUN for U_HOME in "/root" "/home/headless"; do \
  mkdir -p "$U_HOME/.seleniumbase/drivers" "$U_HOME/.local/share/undetected_chromedriver"; \
  cp /usr/bin/chromedriver "$U_HOME/.seleniumbase/drivers/chromedriver"; \
  cp /usr/bin/chromedriver "$U_HOME/.seleniumbase/drivers/uc_driver"; \
  cp /usr/bin/chromedriver "$U_HOME/.local/share/undetected_chromedriver/chromedriver"; \
  done && \
  # 彻底解决系统包路径权限：先创建/拷贝，再执行 chown 和 chmod
  mkdir -p /usr/local/lib/python3.10/dist-packages/seleniumbase/drivers && \
  cp /usr/bin/chromedriver /usr/local/lib/python3.10/dist-packages/seleniumbase/drivers/uc_driver && \
  chown -R headless:headless /usr/local/lib/python3.10/dist-packages/seleniumbase/drivers && \
  chmod -R 777 /usr/local/lib/python3.10/dist-packages/seleniumbase/drivers && \
  chown -R headless:headless /home/headless/.local /home/headless/.seleniumbase

# 锁定关键环境变量
ENV SELENIUMBASE_CHROME_DRIVER_AUTO_DOWNLOAD=False \
  SELENIUMBASE_GECKO_DRIVER_AUTO_DOWNLOAD=False \
  UC_DRIVER_PATH=/usr/local/lib/python3.10/dist-packages/seleniumbase/drivers/uc_driver \
  CHROME_PATH=/usr/bin/google-chrome-stable

USER root
EXPOSE 8080
WORKDIR /app
CMD ["/app/scripts/entrypoint.sh"]
