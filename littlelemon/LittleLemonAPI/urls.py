from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    path('categories/', views.CategoriesView.as_view(), name='categories'),
    path('menu-items/', views.MenuItemsView.as_view(), name='menu-items'),
    path('menu-items/<int:pk>/', views.SingleMenuItemView.as_view(), name='single-menu-item'),
    path('cart/menu-items/', views.CartView.as_view(), name='cart'),
    path('orders/', views.OrdersView.as_view(), name='orders'),
    path('orders/<int:pk>/', views.SingleOrderView.as_view(), name='single-order'),
    path('groups/manager/users/', views.managers, name='managers'),
    path('groups/manager/users/<int:user_id>/', views.remove_manager, name='remove-manager'),
    path('groups/delivery-crew/users/', views.delivery_crew, name='delivery-crew'),
    path('groups/delivery-crew/users/<int:user_id>/', views.remove_delivery_crew, name='remove-delivery-crew'),
]