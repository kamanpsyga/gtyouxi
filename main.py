import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, Cookie

def check_already_extended_error(page):
    """
    检查页面是否显示已经续期过的错误提示
    """
    try:
        # 检查常见的错误提示选择器
        error_selectors = [
            '.alert.alert-danger',
            '.error-message', 
            '.form-error',
            '[role="alert"]',
            '.notification.is-danger',
            '.toast-error',
            'div:has-text("already extended")',
            'div:has-text("once per day")',
            'div:has-text("You have already extended")'
        ]
        
        for selector in error_selectors:
            error_element = page.query_selector(selector)
            if error_element:
                error_text = error_element.inner_text().strip().lower()
                # 检查是否包含已续期相关的关键词
                if any(keyword in error_text for keyword in [
                    'already extended', 
                    'once per day', 
                    'you have already', 
                    '已经续期',
                    '每天只能'
                ]):
                    return True
        
        return False
    except Exception:
        return False

def login_to_panel(page, remember_web_cookie, login_email, login_password):
    """
    登录到 GTX Gaming 控制面板
    返回是否登录成功
    """
    # --- 尝试通过 REMEMBER_WEB_COOKIE 会话登录 ---
    if remember_web_cookie:
        print("尝试使用 REMEMBER_WEB_COOKIE 会话登录...")
        session_cookie = Cookie(
            name='remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
            value=remember_web_cookie,
            domain='.gtxgaming.co.uk',
            path='/',
            expires=time.time() + 3600 * 24 * 365,
            httpOnly=True,
            secure=True,
            sameSite='Lax'
        )
        page.context.add_cookies([session_cookie])
        
        # 测试登录状态，访问主页面
        test_url = "https://gamepanel2.gtxgaming.co.uk/home"
        print(f"正在测试登录状态，访问: {test_url}")
        page.goto(test_url, wait_until="networkidle", timeout=60000)

        # 检查是否成功登录
        if "login" in page.url or "auth" in page.url:
            print("使用 REMEMBER_WEB_COOKIE 登录失败或会话无效。将尝试使用邮箱密码登录。")
            page.context.clear_cookies()
            remember_web_cookie = None
        else:
            print("REMEMBER_WEB_COOKIE 登录成功。")
            return True

    # --- 如果 REMEMBER_WEB_COOKIE 不可用或失败，则回退到邮箱密码登录 ---
    if not remember_web_cookie:
        if not (login_email and login_password):
            print("错误: REMEMBER_WEB_COOKIE 无效，且未提供 LOGIN_EMAIL 或 LOGIN_PASSWORD。无法登录。")
            return False

        login_url = "https://gamepanel2.gtxgaming.co.uk/auth/login"
        print(f"正在访问登录页: {login_url}")
        page.goto(login_url, wait_until="networkidle", timeout=60000)

        # 登录表单元素选择器
        email_selector = 'input[name="email"]'
        password_selector = 'input[name="password"]'
        login_button_selector = 'button[type="submit"]'

        print("正在等待登录元素加载...")
        page.wait_for_selector(email_selector, timeout=30000)
        page.wait_for_selector(password_selector, timeout=30000)
        page.wait_for_selector(login_button_selector, timeout=30000)

        print("正在填充邮箱和密码...")
        page.fill(email_selector, login_email)
        page.fill(password_selector, login_password)

        print("正在点击登录按钮...")
        page.click(login_button_selector)

        # 等待登录完成，检查是否跳转到主页
        try:
            page.wait_for_url("**/home*", timeout=60000)
            print("邮箱密码登录成功。")
            return True
        except Exception:
            error_message_selector = '.alert.alert-danger, .error-message, .form-error'
            error_element = page.query_selector(error_message_selector)
            if error_element:
                error_text = error_element.inner_text().strip()
                print(f"邮箱密码登录失败: {error_text}")
                page.screenshot(path="login_fail_error_message.png")
            else:
                print("邮箱密码登录失败: 未能跳转到预期页面或检测到错误信息。")
                page.screenshot(path="login_fail_no_error.png")
            return False
    
    return False

def extend_server_time(page, server_url, server_name=""):
    """
    为指定服务器延长时间
    返回元组: (是否成功, 状态描述)
    """
    try:
        server_display_name = server_name if server_name else server_url.split('/')[-1]
        server_id = server_url.split('/')[-1]
        print(f"\n=== 正在处理服务器: {server_display_name} ===")
        
        # 导航到服务器页面
        print(f"正在访问服务器页面: {server_url}")
        page.goto(server_url, wait_until="networkidle", timeout=60000)
        
        # 检查是否成功到达服务器页面
        if "login" in page.url or "auth" in page.url:
            print(f"访问服务器 {server_display_name} 失败，会话可能已过期。")
            return False, "failed"
            
        # 查找并点击 "EXTEND 72 HOUR(S)" 按钮
        add_button_selector = 'button:has-text("EXTEND 72 HOUR(S)")'
        print(f"正在查找 'EXTEND 72 HOUR(S)' 按钮...")
        
        try:
            # 检查按钮是否存在且可见
            button_element = page.query_selector(add_button_selector)
            if not button_element:
                # 检查是否有已续期的错误提示
                if check_already_extended_error(page):
                    print(f"ℹ️ 服务器 {server_display_name} 已经续期过了")
                    return True, "already_extended"
                else:
                    print(f"❌ 服务器 {server_display_name} 未找到续期按钮")
                    return False, "failed"
            
            # 检查按钮是否可点击
            if button_element.is_disabled():
                print(f"ℹ️ 服务器 {server_display_name} 续期按钮已禁用（可能已续期）")
                return True, "already_extended"
            
            # 尝试点击按钮
            page.wait_for_selector(add_button_selector, state='visible', timeout=10000)
            
            # 设置网络响应监听
            responses = []
            def handle_response(response):
                if "/api/client/freeservers/" in response.url or "renew" in response.url.lower():
                    responses.append(response)
            
            page.on("response", handle_response)
            
            try:
                # 点击续期按钮
                page.click(add_button_selector)
                
                # 等待页面响应和更新
                time.sleep(5)
                
                # 检查网络响应
                if responses:
                    for response in responses:
                        if response.status == 400:
                            print(f"ℹ️ 服务器 {server_display_name} 已经续期过了 (HTTP 400)")
                            return True, "already_extended"
                        elif response.status == 200:
                            print(f"✅ 服务器 {server_display_name} 成功延长时间 (HTTP 200)")
                            return True, "success"
                        else:
                            print(f"❌ 服务器 {server_display_name} 续期请求返回 HTTP {response.status}")
                
                # 检查页面是否有错误提示
                if check_already_extended_error(page):
                    print(f"ℹ️ 服务器 {server_display_name} 已经续期过了 (页面提示)")
                    return True, "already_extended"
                
                # 如果没有明确的错误提示，假设成功
                print(f"✅ 服务器 {server_display_name} 续期操作完成")
                return True, "success"
                
            finally:
                # 移除响应监听器
                page.remove_listener("response", handle_response)
            
        except Exception as e:
            print(f"❌ 处理服务器 {server_display_name} 时发生异常: {e}")
            # 检查是否有已续期的错误提示
            if check_already_extended_error(page):
                print(f"ℹ️ 服务器 {server_display_name} 已经续期过了")
                return True, "already_extended"
            return False, "failed"
            
    except Exception as e:
        print(f"❌ 处理服务器 {server_display_name} 时发生错误: {e}")
        page.screenshot(path=f"server_error_{server_display_name}.png")
        return False, "failed"

def generate_readme(server_results, timestamp):
    """
    生成 README.md 文件
    server_results: 服务器处理结果列表 [(server_id, status), ...]
    timestamp: 运行时间戳
    """
    readme_content = f"# GTX Gaming 自动续期状态\n\n"
    readme_content += f"**最后运行时间**: `{timestamp}`\n\n"
    readme_content += f"**运行结果**: <br>\n"
    
    for server_id, status in server_results:
        if status == "success":
            icon = "✅"
            message = "续期成功"
        elif status == "already_extended":
            icon = "ℹ️"
            message = "已经续期过了"
        else:  # failed
            icon = "❌"
            message = "续期失败"
        
        readme_content += f"{icon} `{server_id}` {message}\n\n"
    
    # 写入 README.md 文件
    try:
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✅ README.md 文件已生成")
    except Exception as e:
        print(f"❌ 生成 README.md 文件失败: {e}")

def add_server_time(server_configs=None):
    """
    批量为多个服务器延长时间
    server_configs: 服务器配置列表，每个配置包含 url 和可选的 name
    如果为空，则使用环境变量中的配置
    """
    # 获取当前时间戳
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    server_results = []
    
    # 获取环境变量
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')
    login_email = os.environ.get('LOGIN_EMAIL')
    login_password = os.environ.get('LOGIN_PASSWORD')

    # 检查是否提供了任何登录凭据
    if not (remember_web_cookie or (login_email and login_password)):
        print("错误: 缺少登录凭据。请设置 REMEMBER_WEB_COOKIE 或 LOGIN_EMAIL 和 LOGIN_PASSWORD 环境变量。")
        return False

    # 如果没有提供服务器配置，从环境变量中获取
    if server_configs is None:
        server_configs = get_server_configs_from_env()
    
    if not server_configs:
        print("错误: 没有找到任何服务器配置。")
        return False

    print(f"准备处理 {len(server_configs)} 个服务器")
    
    with sync_playwright() as p:
        # 在 GitHub Actions 中，通常使用 headless 模式
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 首先登录
            print("正在登录 GTX Gaming 控制面板...")
            if not login_to_panel(page, remember_web_cookie, login_email, login_password):
                print("登录失败，无法继续执行。")
                # 即使登录失败也要生成README
                for config in server_configs:
                    server_url = config.get('url', '')
                    if server_url:
                        server_id = server_url.split('/')[-1]
                        server_results.append((server_id, "failed"))
                generate_readme(server_results, current_time)
                return False
            
            print("登录成功！开始处理服务器列表...")
            
            # 处理每个服务器
            success_count = 0
            total_count = len(server_configs)
            
            for config in server_configs:
                server_url = config.get('url', '')
                server_name = config.get('name', '')
                
                if not server_url:
                    print(f"跳过无效的服务器配置: {config}")
                    continue
                
                server_id = server_url.split('/')[-1]
                is_success, status = extend_server_time(page, server_url, server_name)
                server_results.append((server_id, status))
                
                if is_success:
                    success_count += 1
                
                # 在处理下一个服务器前稍作等待
                time.sleep(2)
            
            print(f"\n=== 批量处理完成 ===")
            print(f"总计: {total_count} 个服务器")
            print(f"成功: {success_count} 个服务器")
            print(f"失败: {total_count - success_count} 个服务器")
            
            # 生成 README.md 文件
            generate_readme(server_results, current_time)
            
            return success_count > 0

        except Exception as e:
            print(f"执行过程中发生未知错误: {e}")
            page.screenshot(path="general_error.png")
            # 即使出错也要生成README
            for config in server_configs:
                server_url = config.get('url', '')
                if server_url:
                    server_id = server_url.split('/')[-1]
                    if not any(result[0] == server_id for result in server_results):
                        server_results.append((server_id, "failed"))
            generate_readme(server_results, current_time)
            return False
        finally:
            browser.close()

def get_server_configs_from_env():
    """
    从环境变量中获取服务器配置
    支持两种格式:
    1. SERVER_URLS: 逗号分隔的URL列表
    2. SERVER_LIST: JSON格式的服务器配置列表
    """
    import json
    
    # 方式1: 从 SERVER_LIST 环境变量读取 JSON 配置
    server_list_env = os.environ.get('SERVER_LIST')
    if server_list_env:
        try:
            server_configs = json.loads(server_list_env)
            print(f"从 SERVER_LIST 环境变量读取到 {len(server_configs)} 个服务器配置")
            return server_configs
        except json.JSONDecodeError as e:
            print(f"解析 SERVER_LIST JSON 格式失败: {e}")
    
    # 方式2: 从 SERVER_URLS 环境变量读取逗号分隔的URL列表
    server_urls_env = os.environ.get('SERVER_URLS')
    if server_urls_env:
        urls = [url.strip() for url in server_urls_env.split(',') if url.strip()]
        server_configs = []
        for i, url in enumerate(urls):
            server_configs.append({
                'url': url,
                'name': f'Server-{i+1}'
            })
        print(f"从 SERVER_URLS 环境变量读取到 {len(server_configs)} 个服务器URL")
        return server_configs
    
    # 方式3: 兼容旧版本，使用默认服务器
    default_url = "https://gamepanel2.gtxgaming.co.uk/server/fa13b794"
    print("未找到服务器配置环境变量，使用默认服务器")
    return [{'url': default_url, 'name': 'Default-Server'}]

if __name__ == "__main__":
    print("开始执行添加服务器时间任务...")
    success = add_server_time()
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
