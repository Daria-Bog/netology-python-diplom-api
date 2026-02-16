from django.urls import path
from backend.views import RegisterAccount, ConfirmAccount, LoginAccount, PartnerUpdate, ContactView, BasketView

app_name = 'backend'
urlpatterns = [
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('basket', BasketView.as_view(), name='basket'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
]