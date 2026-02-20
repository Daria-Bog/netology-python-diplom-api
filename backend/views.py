from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, ConfirmEmailToken, Order, OrderItem, Contact
from backend.serializers import UserSerializer

import yaml
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.db.models import Sum, F
from backend.serializers import OrderSerializer, OrderItemSerializer
from backend.serializers import ContactSerializer
from backend.signals import new_order_signal
from rest_framework.throttling import AnonRateThrottle

class ContactView(APIView):
    """
    Управление контактами пользователя (адреса доставки и телефоны).
    Поддерживает просмотр, добавление, удаление и редактирование.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request, *args, **kwargs):
        # Создаем новый адрес
        serializer = ContactSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return JsonResponse({'Status': True})
        return JsonResponse({'Status': False, 'Errors': serializer.errors})

    def get(self, request, *args, **kwargs):
        # Смотрим свои адреса
        contacts = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

class BasketView(APIView):
    """
    Класс для управления корзиной пользователя.
    Позволяет просматривать, добавлять, удалять и изменять количество товаров.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    # Посмотреть корзину
    def get(self, request, *args, **kwargs):
        basket = Order.objects.filter(user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # Добавить товар в корзину
    def post(self, request, *args, **kwargs):
        items_dict = request.data.get('items')
        if items_dict:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            objects_created = 0
            for order_item in items_dict:
                order_item.update({'order': basket.id})
                serializer = OrderItemSerializer(data=order_item)
                if serializer.is_valid():
                    serializer.save()
                    objects_created += 1
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})

            return JsonResponse({'Status': True, 'Создано объектов': objects_created})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны аргументы'})

    # Оформить заказ (из корзины в заказ)
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        contact_id = request.data.get('contact_id')
        if contact_id:
            # Находим корзину и обновляем её
            is_updated = Order.objects.filter(
                user_id=request.user.id, state='basket').update(
                contact_id=contact_id,
                state='new'
            )

            if is_updated:
                new_order_signal.send(sender=self.__class__, user_id=request.user.id)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class RegisterAccount(APIView):
    """
    Регистрация новых покупателей.
    Принимает email, пароль и данные пользователя, отправляет токен подтверждения.
    """
    throttle_classes = [AnonRateThrottle]  # Ограничит частоту регистраций для анонимов

    def post(self, request, *args, **kwargs):
        # Проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            # Проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                return JsonResponse({'Status': False, 'Errors': {'password': str(password_error)}})

            data = request.data.copy()
            if 'email' in data and 'username' not in data:
                data['username'] = data['email']

            user_serializer = UserSerializer(data=data)

            if user_serializer.is_valid():
                # Сохраняем пользователя
                user = user_serializer.save()
                user.set_password(request.data['password'])
                user.save()

                # Создаем токен подтверждения
                token, _ = ConfirmEmailToken.objects.get_or_create(user=user)

                # Имитация отправки письма (токен выведется в консоль)
                print(f"Token for {user.email}: {token.key}")

                return JsonResponse(
                    {'Status': True, 'Message': 'Пользователь зарегистрирован. Токен отправлен на почту.'})
            else:
                return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все обязательные аргументы'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    def post(self, request, *args, **kwargs):
        # Проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неверно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все обязательные аргументы'})

class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})

                return JsonResponse({'Status': False, 'Errors': 'Аккаунт не активирован'})

            return JsonResponse({'Status': False, 'Errors': 'Неверный логин или пароль'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все обязательные аргументы'})


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    # Только авторизованные пользователи могут обновлять прайс
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request, *args, **kwargs):
        # В реальности файл загружается через request.files,
        # но для теста прочитаем его из локальной папки
        try:
            with open('shop_data.yaml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)

            for category_data in data['categories']:
                category_obj, _ = Category.objects.get_or_create(id=category_data['id'], name=category_data['name'])
                category_obj.shops.add(shop)

            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                product_info = ProductInfo.objects.create(
                    product_id=product.id,
                    external_id=item['id'],
                    model=item['model'],
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity'],
                    shop_id=shop.id
                )

                for name, value in item['parameters'].items():
                    parameter_obj, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter_obj.id,
                        value=value
                    )

            return JsonResponse({'Status': True, 'Message': 'Прайс успешно загружен'})

        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': str(e)})