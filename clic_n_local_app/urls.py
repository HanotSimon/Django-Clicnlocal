from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('about/', views.about, name='about'),
    path('add_to_cart/<int:produit_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart_detail/', views.cart_detail, name='cart_detail'),
    path('update_cart_item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path("contact/success/", views.contact_success_view, name="contact_success"),
    path('produits/<int:produit_id>', views.produit_detail, name='produit-detail'),
    path("produits", views.ProduitsListView.as_view(), name="produits_list"),
    path("payement/success", views.view_paypal_success, name="payment_success"),
    path("payement/cancel", views.view_paypal_cancel, name="payment_cancel"),
    path("commande/recap/", views.RecapCommandeView.as_view(), name="recap_commande"),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/success/', views.inscription_succes_view, name='inscription_succes'),
    path('login/', views.ClientLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path("profile/password_change/", views.MyPasswordChangeView.as_view(),name="password_change",),
    path("profile/password_change/done/",auth_views.PasswordChangeDoneView.as_view(template_name="password_change_done.html"),name="password_change_done",),
]