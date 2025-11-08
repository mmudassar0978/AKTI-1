from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from .models import Category, MenuItem, Cart, Order, OrderItem
from .serializers import CategorySerializer, MenuItemSerializer, CartSerializer, OrderSerializer, UserSerializer
from .permissions import IsManager, IsDeliveryCrew
import datetime

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'featured']
    ordering_fields = ['price', 'title']
    search_fields = ['title', 'category__title']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = MenuItem.objects.all()
        category = self.request.query_params.get('category', None)
        featured = self.request.query_params.get('featured', None)
        
        if category:
            queryset = queryset.filter(category=category)
        if featured is not None:
            queryset = queryset.filter(featured=featured)
            
        return queryset.order_by('id')

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def delete(self, request):
        Cart.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrdersView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'date']
    
    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=user)
        else:
            return Order.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        # Get cart items
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return Response({"error": "No items in cart"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate total
        total = sum(item.price for item in cart_items)
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total=total,
            date=datetime.date.today()
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=cart_item.menuitem,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                price=cart_item.price
            )
        
        # Clear cart
        cart_items.delete()
        
        # Serialize and return order
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SingleOrderView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=user)
        else:
            return Order.objects.filter(user=user)
    
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        user = request.user
        
        # Managers can update delivery crew and featured status
        if user.groups.filter(name='Manager').exists():
            delivery_crew_id = request.data.get('delivery_crew')
            if delivery_crew_id:
                delivery_crew = get_object_or_404(User, id=delivery_crew_id)
                if delivery_crew.groups.filter(name='Delivery Crew').exists():
                    order.delivery_crew = delivery_crew
            
            status_value = request.data.get('status')
            if status_value is not None:
                order.status = status_value
                
            order.save()
            serializer = self.get_serializer(order)
            return Response(serializer.data)
        
        # Delivery crew can only update status
        elif user.groups.filter(name='Delivery Crew').exists() and order.delivery_crew == user:
            status_value = request.data.get('status')
            if status_value is not None:
                order.status = status_value
                order.save()
                serializer = self.get_serializer(order)
                return Response(serializer.data)
            else:
                return Response({"error": "Only status can be updated"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Regular users cannot update orders
        else:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def managers(request):
    managers_group = Group.objects.get(name='Manager')
    
    if request.method == 'GET':
        # Return all managers
        managers = managers_group.user_set.all()
        serializer = UserSerializer(managers, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Assign user to managers group
        username = request.data.get('username')
        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(User, username=username)
        managers_group.user_set.add(user)
        return Response({"message": f"User {username} added to Manager group"}, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def remove_manager(request, user_id):
    managers_group = Group.objects.get(name='Manager')
    user = get_object_or_404(User, id=user_id)
    managers_group.user_set.remove(user)
    return Response({"message": f"User {user.username} removed from Manager group"}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsManager])
def delivery_crew(request):
    delivery_group = Group.objects.get(name='Delivery Crew')
    
    if request.method == 'GET':
        # Return all delivery crew members
        delivery_crew = delivery_group.user_set.all()
        serializer = UserSerializer(delivery_crew, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Assign user to delivery crew group
        username = request.data.get('username')
        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(User, username=username)
        delivery_group.user_set.add(user)
        return Response({"message": f"User {username} added to Delivery Crew group"}, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsManager])
def remove_delivery_crew(request, user_id):
    delivery_group = Group.objects.get(name='Delivery Crew')
    user = get_object_or_404(User, id=user_id)
    delivery_group.user_set.remove(user)
    return Response({"message": f"User {user.username} removed from Delivery Crew group"}, status=status.HTTP_200_OK)