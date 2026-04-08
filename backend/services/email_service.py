"""
Email Service - Gửi email cho người dùng (account creation, password reset, etc.)
"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service để gửi email thông báo"""
    
    @staticmethod
    def send_account_creation_email(user, temporary_password: str) -> bool:
        """
        Gửi email cho user khi admin tạo account mới
        
        Args:
            user: Account object vừa được tạo
            temporary_password: Mật khẩu tạm gợi ý
        
        Returns:
            bool: True nếu gửi thành công, False nếu lỗi
        """
        try:
            subject = "[RAG System] Tài khoản đã được tạo"
            
            # Build email context
            context = {
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'temporary_password': temporary_password,
                'login_url': f"{settings.FRONTEND_URL}/login",
                'app_name': 'RAG System',
                'frontend_url': settings.FRONTEND_URL,
            }
            
            # Render HTML email template
            html_message = EmailService._render_account_creation_template(context)
            
            # Plain text message as fallback
            message = f"""
Xin chào {context['full_name']},

Admin đã tạo tài khoản cho bạn trên hệ thống RAG System.

Thông tin tài khoản:
- Username: {context['username']}
- Email: {context['email']}
- Mật khẩu tạm: {context['temporary_password']}

Vui lòng đăng nhập tại: {context['login_url']}

Sau khi đăng nhập, bạn nên thay đổi mật khẩu ngay để bảo mật tài khoản.

Nếu bạn không thực hiện yêu cầu này, vui lòng liên hệ quản trị viên.

---
RAG System Admin
            """
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Account creation email sent to {user.email} (user: {user.username})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send account creation email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _render_account_creation_template(context: dict) -> str:
        """Render HTML template cho email tạo account"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 4px; text-align: center; }}
                .content {{ padding: 20px 0; }}
                .info-box {{ background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; }}
                .info-box strong {{ color: #667eea; }}
                .password-box {{ background: #fffbf0; padding: 15px; border: 2px solid #ff9800; border-radius: 4px; margin: 15px 0; }}
                .password-box .label {{ color: #ff6600; font-weight: bold; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
                .footer {{ text-align: center; padding: 20px 0; color: #999; font-size: 12px; border-top: 1px solid #eee; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Chào mừng đến với {context['app_name']}</h1>
                </div>
                
                <div class="content">
                    <p>Xin chào <strong>{context['full_name']}</strong>,</p>
                    
                    <p>Admin đã tạo tài khoản mới cho bạn trên hệ thống {context['app_name']}. Dưới đây là thông tin đăng nhập:</p>
                    
                    <div class="info-box">
                        <p><strong>Username:</strong> {context['username']}</p>
                        <p><strong>Email:</strong> {context['email']}</p>
                    </div>
                    
                    <div class="password-box">
                        <p class="label">Mật khẩu tạm (Vui lòng thay đổi ngay):</p>
                        <p style="font-size: 16px; font-weight: bold; word-break: break-all;">{context['temporary_password']}</p>
                    </div>
                    
                    <p><strong>Lưu ý quan trọng:</strong></p>
                    <ul>
                        <li>Bạn nên thay đổi mật khẩu ngay sau khi đăng nhập lần đầu</li>
                        <li>Giữ bí mật mật khẩu của bạn</li>
                        <li>Không chia sẻ thông tin đăng nhập với bất kỳ ai</li>
                    </ul>
                    
                    <a href="{context['login_url']}" class="button">Đăng nhập ngay</a>
                    
                    <p style="margin-top: 20px;">Nếu bạn không thực hiện yêu cầu này, vui lòng liên hệ quản trị viên.</p>
                </div>
                
                <div class="footer">
                    <p>&copy; 2026 {context['app_name']}. Bảo vệ bởi hệ thống bảo mật hàng đầu.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def send_password_reset_email(user, reset_token: str) -> bool:
        """
        Gửi email reset password khi user quên mật khẩu
        
        Args:
            user: Account object
            reset_token: Password reset token
        
        Returns:
            bool: True if success, False if failed
        """
        try:
            subject = "[RAG System] Yêu cầu đặt lại mật khẩu"
            
            # Build reset link
            reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
            
            context = {
                'full_name': user.get_full_name() or user.username,
                'email': user.email,
                'reset_link': reset_link,
                'app_name': 'RAG System',
                'frontend_url': settings.FRONTEND_URL,
                'token': reset_token,
            }
            
            # HTML message
            html_message = EmailService._render_password_reset_template(context)
            
            # Plain text message
            message = f"""
Xin chào {context['full_name']},

Chúng tôi nhận được yêu cầu đặt lại mật khẩu từ địa chỉ email này.

Vui lòng nhấp vào liên kết bên dưới để đặt lại mật khẩu:
{reset_link}

Hoặc nhập mã token này: {reset_token}

Lưu ý: Liên kết này sẽ hết hạn trong 24 giờ.

Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này hoặc liên hệ quản trị viên.

---
RAG System
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _render_password_reset_template(context: dict) -> str:
        """Render HTML template for password reset email"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 4px; text-align: center; }}
                .content {{ padding: 20px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 4px; margin: 15px 0; color: #856404; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #f5576c; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .token-box {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #f5576c; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px 0; color: #999; font-size: 12px; border-top: 1px solid #eee; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Đặt lại mật khẩu</h1>
                </div>
                
                <div class="content">
                    <p>Xin chào <strong>{context['full_name']}</strong>,</p>
                    
                    <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu của bạn trên hệ thống {context['app_name']}.</p>
                    
                    <div class="warning">
                        <strong>Lưu ý:</strong> Liên kết này sẽ hết hạn trong <strong>24 giờ</strong>. Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này.
                    </div>
                    
                    <p>Nhấp vào nút bên dưới để đặt lại mật khẩu:</p>
                    <a href="{context['reset_link']}" class="button">Đặt lại mật khẩu</a>
                    
                    <p style="margin-top: 20px;">Nếu nút không hoạt động, vui lòng sao chép và dán liên kết sau vào trình duyệt:</p>
                    <div class="token-box">
                        <p style="word-break: break-all;">{context['reset_link']}</p>
                    </div>
                    
                    <p>Hoặc sử dụng mã token này: <strong style="word-break: break-all;">{context['token']}</strong></p>
                    
                    <p style="margin-top: 20px;"><strong>Bảo mật:</strong></p>
                    <ul>
                        <li>Không bao giờ chia sẻ liên kết đặt lại này với bất kỳ ai</li>
                        <li>Kiểm tra email của người gửi trước khi nhấp vào liên kết</li>
                        <li>Nếu không nhận ra yêu cầu, hãy thay đổi mật khẩu ngay</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>&copy; 2026 {context['app_name']}. Bảo vệ bởi hệ thống bảo mật hàng đầu.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def send_admin_password_reset_email(user, new_password: str = None) -> bool:
        """
        Gửi email thông báo khi admin reset password cho user
        
        Args:
            user: Account object whose password was reset
            new_password: Mật khẩu mới (nếu có thì gửi trong email)
        
        Returns:
            bool: True if success, False if failed
        """
        try:
            subject = "[RAG System] Mật khẩu của bạn đã được đặt lại bởi quản trị viên"
            
            login_url = f"{settings.FRONTEND_URL}/login"
            
            context = {
                'full_name': user.get_full_name() or user.username,
                'username': user.username,
                'email': user.email,
                'login_url': login_url,
                'app_name': 'RAG System',
                'new_password': new_password,
            }
            
            # HTML message
            html_message = EmailService._render_admin_password_reset_template(context)
            
            # Plain text message
            if new_password:
                message = f"""
Xin chào {context['full_name']},

Quản trị viên đã đặt lại mật khẩu của tài khoản của bạn trên hệ thống {context['app_name']}.

THÔNG TIN ĐĂNG NHẬP MỚI:
- Username: {context['username']}
- Mật khẩu mới: {new_password}

Vui lòng đăng nhập tại: {login_url}

⚠️ QUAN TRỌNG: 
- Sau khi đăng nhập thành công, bạn PHẢI thay đổi mật khẩu ngay tức thì để bảo mật tài khoản
- Đừng chia sẻ mật khẩu này cho bất kỳ ai
- Nếu bạn không nhận ra yêu cầu này, vui lòng liên hệ quản trị viên ngay

---
RAG System
                """
            else:
                message = f"""
Xin chào {context['full_name']},

Quản trị viên đã đặt lại mật khẩu của tài khoản của bạn trên hệ thống {context['app_name']}.

Vui lòng sử dụng tính năng "Quên mật khẩu" hoặc liên hệ quản trị viên để lấy mật khẩu mới.

Đăng nhập: {login_url}

Nếu bạn không nhận ra yêu cầu này, vui lòng liên hệ quản trị viên ngay.

---
RAG System
                """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Admin password reset email sent to {user.email} (with new password: {bool(new_password)})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send admin password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _render_admin_password_reset_template(context: dict) -> str:
        """Render HTML template for admin password reset notification"""
        
        # If new password is provided, show it in the email
        password_section = ""
        if context.get('new_password'):
            password_section = f"""
                    <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <p style="color: #856404; margin: 0;"><strong>⚠️ THÔNG TIN ĐĂNG NHẬP MỚI:</strong></p>
                        <table style="width: 100%; margin-top: 10px;">
                            <tr>
                                <td style="font-weight: bold; color: #856404;">Username:</td>
                                <td style="color: #333;">{context['username']}</td>
                            </tr>
                            <tr>
                                <td style="font-weight: bold; color: #856404;">Mật khẩu mới:</td>
                                <td style="background: #fff8e1; padding: 8px; border-radius: 3px; font-family: monospace; color: #333;"><strong>{context['new_password']}</strong></td>
                            </tr>
                        </table>
                        <p style="color: #856404; margin: 10px 0 0 0; font-size: 12px;">
                            <strong>Quan trọng:</strong> Hãy thay đổi mật khẩu ngay sau khi đăng nhập lần đầu tiên để bảo mật tài khoản của bạn.
                        </p>
                    </div>
            """
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: #333; padding: 20px; border-radius: 4px; text-align: center; }}
                .content {{ padding: 20px 0; }}
                .info-box {{ background: #e8f5e9; border: 1px solid #4caf50; padding: 15px; border-radius: 4px; margin: 15px 0; color: #2e7d32; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #fa709a; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; text-align: center; }}
                .footer {{ text-align: center; padding: 20px 0; color: #999; font-size: 12px; border-top: 1px solid #eee; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Mật khẩu đã được đặt lại bởi quản trị viên</h1>
                </div>
                
                <div class="content">
                    <p>Xin chào <strong>{context['full_name']}</strong>,</p>
                    
                    <p>Quản trị viên hệ thống đã yêu cầu đặt lại mật khẩu của tài khoản của bạn trên {context['app_name']}.</p>
                    
                    {password_section}
                    
                    <a href="{context['login_url']}" class="button">👉 Đến trang đăng nhập</a>
                    
                    <div class="info-box">
                        <strong>Các bước tiếp theo:</strong>
                        <ol>
                            <li>Sao chép mật khẩu mới ở trên</li>
                            <li>Đăng nhập tại <a href="{context['login_url']}">{context['login_url']}</a></li>
                            <li><strong>NGAY SAU KHI đăng nhập, hãy đổi mật khẩu thành mật khẩu mạnh của riêng bạn</strong></li>
                            <li>Đừng chia sẻ mật khẩu này cho bất kỳ ai</li>
                        </ol>
                    </div>
                    
                    <p style="margin-top: 20px;"><strong>🔒 Lưu ý bảo mật:</strong></p>
                    <ul>
                        <li>Chỉ quản trị viên mới có thể yêu cầu đặt lại mật khẩu</li>
                        <li>Nếu bạn không nhận ra yêu cầu này, hãy liên hệ quản trị viên ngay lập tức</li>
                        <li>Không bao giờ chia sẻ mật khẩu của bạn qua email hoặc số điện thoại</li>
                        <li>Hãy thay đổi mật khẩu thường xuyên để bảo mật tài khoản</li>
                    </ul>
                    
                    <p style="margin-top: 20px;">Nếu bạn có bất kỳ câu hỏi nào, vui lòng liên hệ bộ phận hỗ trợ quản trị viên.</p>
                </div>
                
                <div class="footer">
                    <p>&copy; 2026 {context['app_name']}. Bảo vệ bởi hệ thống bảo mật hàng đầu.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
