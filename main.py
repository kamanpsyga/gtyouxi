#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GTX Gaming 自动登录和续期脚本
"""

# =====================================================================
#                           导入依赖
# =====================================================================

import os
import time
import json
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, Cookie

# =====================================================================
#                           配置区域
# =====================================================================

# 登录配置 - 优先从环境变量读取，确保安全性
REMEMBER_WEB_COOKIE = os.getenv('REMEMBER_WEB_COOKIE', "")  # 优先使用环境变量
LOGIN_EMAIL = os.getenv('LOGIN_EMAIL', "")  # 邮箱登录
LOGIN_PASSWORD = os.getenv('LOGIN_PASSWORD', "")  # 密码登录

# 服务器配置
SERVER_LIST = os.getenv('SERVER_LIST', "")  # JSON格式的服务器列表

# 网址配置
BASE_URL = 'https://gamepanel2.gtxgaming.co.uk'
LOGIN_URL = 'https://gamepanel2.gtxgaming.co.uk/auth/login'
HOME_URL = 'https://gamepanel2.gtxgaming.co.uk/home'

# 运行配置
HEADLESS = True  # 默认无头模式，适合自动化环境
SCREENSHOT_ENABLED = True  # 是否启用截图功能

# =====================================================================
#                    GTX Gaming 自动续期主类
# =====================================================================

class GTXGamingRenewer:
    """GTX Gaming 自动续期主类"""
    
    def __init__(self):
        """初始化续期器"""
        self.browser = None
        self.context = None
        self.page = None
        self.server_results = []
        
    # =================================================================
    #                       1. 配置验证模块
    # =================================================================
    
    def validate_config(self):
        """验证配置"""
        if not (REMEMBER_WEB_COOKIE or (LOGIN_EMAIL and LOGIN_PASSWORD)):
            raise ValueError("请设置 REMEMBER_WEB_COOKIE 或 LOGIN_EMAIL + LOGIN_PASSWORD")
        
        server_configs = self.get_server_configs()
        if not server_configs:
            raise ValueError("请设置 SERVER_LIST 环境变量")
            
        print("✅ 配置验证通过")
        return True
    
    # =================================================================
    #                       2. 浏览器初始化模块
    # =================================================================
    
    def init_browser(self):
        """初始化浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=HEADLESS)
            self.page = self.browser.new_page()
            print("✅ 浏览器初始化成功")
        except Exception as e:
            print(f"❌ 浏览器初始化失败: {e}")
            raise
    
    # =================================================================
    #                       3. 登录验证模块
    # =================================================================
    
    def login_to_panel(self):
        """登录到 GTX Gaming 控制面板"""
        # 优先尝试 Cookie 登录
        if REMEMBER_WEB_COOKIE:
            if self._login_with_cookie():
                return True
            print("🔄 Cookie 登录失败，尝试邮箱密码登录...")
        
        # 邮箱密码登录
        if LOGIN_EMAIL and LOGIN_PASSWORD:
            return self._login_with_credentials()
        
        print("❌ 所有登录方式都失败")
        return False
    
    def _login_with_cookie(self):
        """使用 Cookie 登录"""
        try:
            print("🍪 尝试使用 Cookie 登录...")
            
            # 设置 Cookie
            session_cookie = Cookie(
                name='remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                value=REMEMBER_WEB_COOKIE,
                domain='.gtxgaming.co.uk',
                path='/',
                expires=time.time() + 3600 * 24 * 365,
                httpOnly=True,
                secure=True,
                sameSite='Lax'
            )
            self.page.context.add_cookies([session_cookie])
            
            # 测试登录状态
            self.page.goto(HOME_URL, wait_until="networkidle", timeout=60000)
            
            if "login" not in self.page.url and "auth" not in self.page.url:
                print("✅ Cookie 登录成功")
                return True
            else:
                print("❌ Cookie 登录失败")
                self.page.context.clear_cookies()
                return False
                
        except Exception as e:
            print(f"❌ Cookie 登录异常: {e}")
            return False
    
    def _login_with_credentials(self):
        """使用邮箱密码登录"""
        try:
            print("📧 尝试使用邮箱密码登录...")
            
            self.page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
            
            # 填写登录表单
            self.page.fill('input[name="email"]', LOGIN_EMAIL)
            self.page.fill('input[name="password"]', LOGIN_PASSWORD)
            self.page.click('button[type="submit"]')
            
            # 等待登录完成
            self.page.wait_for_url("**/home*", timeout=60000)
            print("✅ 邮箱密码登录成功")
            return True
            
        except Exception as e:
            print(f"❌ 邮箱密码登录失败: {e}")
            if SCREENSHOT_ENABLED:
                print("📸 保存登录失败截图: login_failed.png")
                self.page.screenshot(path="login_failed.png", full_page=True)
            return False
    
    # =================================================================
    #                       4. 到期时间获取模块
    # =================================================================
    
    def get_server_expire_time(self):
        """获取服务器到期时间"""
        try:
            print("🔍 正在获取服务器到期时间...")
            
            element = self.page.wait_for_selector('p:has-text("Expiry Date")', timeout=5000)
            if not element or not element.is_visible():
                print("❌ 未找到到期时间元素")
                return None
            
            text_content = element.text_content().strip()
            print(f"🎯 找到到期时间元素: {text_content}")
            
            # 使用正则表达式提取时间格式 YYYY-MM-DD HH:MM:SS
            pattern = r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
            match = re.search(pattern, text_content)
            
            if match:
                expire_time = match.group()
                print(f"✅ 成功获取到期时间: {expire_time}")
                return expire_time
            else:
                print(f"⚠️ 未找到匹配的时间格式，原文本: {text_content}")
                return None
                
        except Exception as e:
            print(f"❌ 获取到期时间失败: {e}")
            return None
    
    # =================================================================
    #                       5. 错误检测模块
    # =================================================================
    
    def check_already_extended_error(self):
        """检查页面是否显示已经续期过的错误提示"""
        try:
            error_selectors = [
                '.alert.alert-danger',
                '.error-message', 
                '.form-error',
                '[role="alert"]',
                'div:has-text("already extended")',
                'div:has-text("once per day")',
                'div:has-text("You have already extended")'
            ]
            
            for selector in error_selectors:
                element = self.page.query_selector(selector)
                if element:
                    error_text = element.inner_text().strip().lower()
                    keywords = ['already extended', 'once per day', 'you have already', '已经续期', '每天只能']
                    if any(keyword in error_text for keyword in keywords):
                        return True
            return False
        except Exception:
            return False
    
    # =================================================================
    #                       6. 服务器续期模块
    # =================================================================
    
    def extend_server_time(self, server_url, server_name=""):
        """为指定服务器延长时间"""
        server_display_name = server_name or server_url.split('/')[-1]
        server_id = server_url.split('/')[-1]
        
        print(f"\n=== 正在处理服务器: {server_display_name} ===")
        
        try:
            # 导航到服务器页面
            print(f"正在访问服务器页面: {server_url}")
            self.page.goto(server_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)  # 等待页面完全加载
            
            # 检查是否成功到达服务器页面
            if "login" in self.page.url or "auth" in self.page.url:
                print(f"❌ 访问服务器失败，会话可能已过期")
                return self._create_result(server_id, "failed", server_name)
            
            # 获取续期前的到期时间
            old_expire_time = self.get_server_expire_time()
            if old_expire_time:
                print(f"📅 续期前到期时间: {old_expire_time}")
            
            # 续期前截图
            if SCREENSHOT_ENABLED:
                before_screenshot = f"{server_id}_before.png"
                print(f"📸 保存续期前截图: {before_screenshot}")
                self.page.screenshot(path=before_screenshot, full_page=True)
            
            # 执行续期操作
            renew_result = self._perform_renew_action()
            
            if renew_result == "success":
                # 获取续期后的到期时间
                new_expire_time = self._get_new_expire_time(old_expire_time)
                
                # 续期后截图
                if SCREENSHOT_ENABLED:
                    after_screenshot = f"{server_id}_after.png"
                    print(f"📸 保存续期后截图: {after_screenshot}")
                    self.page.screenshot(path=after_screenshot, full_page=True)
                
                return self._create_result(server_id, "success", server_name, old_expire_time, new_expire_time)
            else:
                # 如果续期失败或已续期，也保存一张截图作为记录
                if SCREENSHOT_ENABLED:
                    status_screenshot = f"{server_id}_status.png"
                    print(f"📸 保存状态截图: {status_screenshot}")
                    self.page.screenshot(path=status_screenshot, full_page=True)
                
                return self._create_result(server_id, renew_result, server_name, old_expire_time)
                
        except Exception as e:
            print(f"❌ 处理服务器 {server_display_name} 时发生错误: {e}")
            if SCREENSHOT_ENABLED:
                error_screenshot = f"{server_id}_error.png"
                print(f"📸 保存错误截图: {error_screenshot}")
                self.page.screenshot(path=error_screenshot, full_page=True)
            return self._create_result(server_id, "failed", server_name)
    
    def _perform_renew_action(self):
        """执行续期按钮点击操作"""
        add_button_selector = 'button:has-text("EXTEND 72 HOUR(S)")'
        print("🔍 正在查找续期按钮...")
        
        # 检查按钮是否存在
        button_element = self.page.query_selector(add_button_selector)
        if not button_element:
            if self.check_already_extended_error():
                print("ℹ️ 服务器已经续期过了")
                return "already_extended"
            else:
                print("❌ 未找到续期按钮")
                return "failed"
        
        # 检查按钮是否可点击
        if button_element.is_disabled():
            print("ℹ️ 续期按钮已禁用（可能已续期）")
            return "already_extended"
        
        # 点击续期按钮
        try:
            print("🖱️ 点击续期按钮...")
            self.page.wait_for_selector(add_button_selector, state='visible', timeout=10000)
            
            # 监听网络响应
            responses = []
            def handle_response(response):
                if "/api/client/freeservers/" in response.url or "renew" in response.url.lower():
                    responses.append(response)
            
            self.page.on("response", handle_response)
            
            try:
                button_element.click()
                time.sleep(5)  # 等待响应
                
                # 检查响应结果
                return self._check_renew_response(responses)
                
            finally:
                self.page.remove_listener("response", handle_response)
                
        except Exception as e:
            print(f"❌ 续期按钮操作失败: {e}")
            if self.check_already_extended_error():
                return "already_extended"
            return "failed"
    
    def _check_renew_response(self, responses):
        """检查续期响应结果"""
        for response in responses:
            if response.status == 400:
                print("ℹ️ 服务器已经续期过了 (HTTP 400)")
                return "already_extended"
            elif response.status == 200:
                print("✅ 服务器成功延长时间 (HTTP 200)")
                return "success"
            else:
                print(f"❌ 续期请求返回 HTTP {response.status}")
        
        # 检查页面错误提示
        if self.check_already_extended_error():
            print("ℹ️ 服务器已经续期过了 (页面提示)")
            return "already_extended"
        
        # 假设成功
        print("✅ 续期操作完成")
        return "success"
    
    def _get_new_expire_time(self, old_expire_time):
        """获取续期后的新到期时间"""
        print("🔄 获取续期后的新到期时间...")
        time.sleep(3)  # 等待页面更新
        
        new_expire_time = self.get_server_expire_time()
        if new_expire_time:
            print(f"📅 续期后到期时间: {new_expire_time}")
            if old_expire_time and new_expire_time != old_expire_time:
                print(f"✅ 确认到期时间已更新: {old_expire_time} → {new_expire_time}")
            else:
                print("ℹ️ 到期时间暂未更新（可能需要等待）")
        else:
            print("⚠️ 无法获取续期后的到期时间")
        
        return new_expire_time
    
    def _create_result(self, server_id, status, server_name, old_expire=None, new_expire=None):
        """创建处理结果"""
        return (server_id, status, old_expire, new_expire, server_name)
    
    # =================================================================
    #                       7. 工具函数模块
    # =================================================================
    
    def get_server_configs(self):
        """从环境变量中获取服务器配置"""
        server_list_env = os.environ.get('SERVER_LIST')
        if not server_list_env:
            print("❌ 未找到 SERVER_LIST 环境变量")
            print("💡 请设置 SERVER_LIST 环境变量以配置您的服务器列表")
            return []
        
        try:
            server_configs = json.loads(server_list_env)
            print(f"从 SERVER_LIST 环境变量读取到 {len(server_configs)} 个服务器配置")
            return server_configs
        except json.JSONDecodeError as e:
            print(f"❌ 解析 SERVER_LIST JSON 格式失败: {e}")
            print("💡 请检查 JSON 格式是否正确")
            return []
    
    def generate_readme(self, timestamp):
        """生成 README.md 文件"""
        # 转换为北京时间（UTC+8）
        try:
            utc_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            beijing_time = utc_time + timedelta(hours=8)
            beijing_timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            beijing_timestamp = timestamp
        
        readme_content = f"**最后运行时间**: `{beijing_timestamp}`\n\n"
        readme_content += f"**运行结果**: <br>\n"
        
        for i, result in enumerate(self.server_results):
            server_id, status, old_expire, new_expire, server_name = result
            
            # 状态图标和文本
            status_map = {
                "success": ("✅", "Success"),
                "already_extended": ("ℹ️", "Unexpired"),
                "failed": ("❌", "Failed")
            }
            status_icon, status_text = status_map.get(status, ("❌", "Failed"))
            
            # 生成服务器信息
            if server_name:
                readme_content += f"🖥️服务器ID：`{server_name}({server_id})`<br>"
            else:
                readme_content += f"🖥️服务器ID：`{server_id}`<br>"
            
            readme_content += f"📊续期结果：{status_icon}{status_text}<br>"
            
            # 添加到期时间信息
            if old_expire:
                readme_content += f"🕛️旧到期时间：`{old_expire}`<br>"
            if new_expire and new_expire != old_expire:
                readme_content += f"🕡️新到期时间：`{new_expire}`<br>"
            
            # 添加服务器之间的空行分隔（最后一个服务器除外）
            if i < len(self.server_results) - 1:
                readme_content += "\n"
            
            readme_content += "\n"
        
        # 写入文件
        try:
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print("✅ README.md 文件已生成")
        except Exception as e:
            print(f"❌ 生成 README.md 文件失败: {e}")
    
    # =================================================================
    #                       8. 资源清理模块
    # =================================================================
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
            print("✅ 浏览器已关闭")
        except Exception as e:
            print(f"❌ 关闭浏览器时发生错误: {e}")
    
    # =================================================================
    #                       9. 主运行流程
    # =================================================================
    
    def run(self):
        """运行主流程"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            print("🚀 启动 GTX Gaming 自动续期脚本")
            print("=" * 50)
            
            # 验证配置
            self.validate_config()
            
            # 初始化浏览器
            print("🌐 初始化浏览器...")
            self.init_browser()
            
            # 登录
            print("🔐 开始登录...")
            if not self.login_to_panel():
                print("❌ 登录失败，无法继续执行")
                return False
            
            print("✅ 登录成功！开始处理服务器列表...")
            
            # 处理每个服务器
            server_configs = self.get_server_configs()
            success_count = 0
            
            for config in server_configs:
                server_url = config.get('url', '')
                server_name = config.get('name', '')
                
                if not server_url:
                    print(f"⚠️ 跳过无效的服务器配置: {config}")
                    continue
                
                result = self.extend_server_time(server_url, server_name)
                self.server_results.append(result)
                
                if result[1] in ["success", "already_extended"]:
                    success_count += 1
                
                time.sleep(2)  # 间隔处理
            
            # 显示总结
            total_count = len(server_configs)
            print(f"\n=== 批量处理完成 ===")
            print(f"总计: {total_count} 个服务器")
            print(f"成功: {success_count} 个服务器")
            print(f"失败: {total_count - success_count} 个服务器")
            
            if SCREENSHOT_ENABLED:
                print(f"📸 截图已保存，每个服务器最多2张截图")
            
            return success_count > 0
            
        except Exception as e:
            print(f"💥 运行时发生错误: {e}")
            return False
        finally:
            # 生成报告
            self.generate_readme(current_time)
            # 清理资源
            self.close()

# =====================================================================
#                          程序启动点
# =====================================================================

if __name__ == "__main__":
    print("开始执行 GTX Gaming 服务器续期任务...")
    renewer = GTXGamingRenewer()
    success = renewer.run()
    
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
