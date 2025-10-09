# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('ai/', views.ai_suggestions_view, name='ai_suggestions'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('2fa/', views.two_factor_view, name='two_factor'),
    # path('ai-suggestions/', views.ai_suggestions_view, name='ai_suggestions'),
    path('generate_poster/', views.poster_generator_view, name='generate_poster'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('generate-video/', views.generate_video_view, name='generate_video'),
    
    # Email Verification & Festival Notifications
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('toggle-notifications/', views.toggle_notifications, name='toggle_notifications'),
    path('unsubscribe/<int:user_id>/', views.unsubscribe_view, name='unsubscribe'),
    path('manage-festivals/', views.manage_festivals_view, name='manage_festivals'),
    path('preview-verification-email/', views.preview_verification_email, name='preview_verification_email'),
    path('preview-festival-notification/', views.preview_festival_notification, name='preview_festival_notification'),
    path('email-templates/', views.email_templates_view, name='email_templates'),
    path('email-subjects/', views.email_subjects_view, name='email_subjects'),
    path('history/', views.user_history_view, name='user_history'),
    path('insights/', views.insights_view, name='insights'),
    
    # path('healthz/', views.health_check, name='health_check'),
]
