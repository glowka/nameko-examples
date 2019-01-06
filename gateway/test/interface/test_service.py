import json

from mock import call

from gateway.exceptions import OrderNotFound, ProductNotFound


class TestGetProduct(object):
    def test_can_get_product(self, alt_gateway_service):
        gateway_service = alt_gateway_service
        gateway_service.products_rpc.get.return_value = {
            "in_stock": 10,
            "maximum_speed": 5,
            "id": "the_odyssey",
            "passenger_capacity": 101,
            "title": "The Odyssey"
        }

        from nameko.extensions import ENTRYPOINT_EXTENSIONS_ATTR
        from werkzeug.test import EnvironBuilder
        from nameko.web.server import WebServer

        wsgi_environ = EnvironBuilder(path='/products/the_odyssey').get_environ()

        from werkzeug.test import run_wsgi_app
        service = gateway_service.container.service_cls()
        server = gateway_service.container.shared_extensions[WebServer]
        get_product_method = service.get_product
        get_product_entrypoint = list(getattr(get_product_method, ENTRYPOINT_EXTENSIONS_ATTR)).pop()
        get_product_entrypoint = get_product_entrypoint.bind(gateway_service.container, 'get_product')
        get_product_entrypoint.server = server
        get_product_entrypoint.setup()
        wsgi_app = server.get_wsgi_app()
        body_iterator, status, headers = run_wsgi_app(wsgi_app, wsgi_environ, lambda status, headers: None)

        print(list(body_iterator))
        print(status)
        print(headers)

        res_json = json.loads(list(body_iterator).pop())
        status_code, status_msg = status.split()

        # response = web_session.get('/products/the_odyssey')
        assert int(status_code) == 200
        assert gateway_service.products_rpc.get.call_args_list == [
            call("the_odyssey")
        ]
        assert res_json == {
            "in_stock": 10,
            "maximum_speed": 5,
            "id": "the_odyssey",
            "passenger_capacity": 101,
            "title": "The Odyssey"
        }

    def test_product_not_found(self, gateway_service, web_session):
        gateway_service.products_rpc.get.side_effect = (
            ProductNotFound('missing'))

        # call the gateway service to get order #1
        response = web_session.get('/products/foo')
        assert response.status_code == 404
        payload = response.json()
        assert payload['error'] == 'PRODUCT_NOT_FOUND'
        assert payload['message'] == 'missing'


class TestCreateProduct(object):
    def test_can_create_product(self, gateway_service, web_session):
        response = web_session.post(
            '/products',
            json.dumps({
                "in_stock": 10,
                "maximum_speed": 5,
                "id": "the_odyssey",
                "passenger_capacity": 101,
                "title": "The Odyssey"
            })
        )
        assert response.status_code == 200
        assert response.json() == {'id': 'the_odyssey'}
        assert gateway_service.products_rpc.create.call_args_list == [call({
                "in_stock": 10,
                "maximum_speed": 5,
                "id": "the_odyssey",
                "passenger_capacity": 101,
                "title": "The Odyssey"
            })]

    def test_create_product_fails_with_invalid_json(
        self, gateway_service, web_session
    ):
        response = web_session.post(
            '/products', 'NOT-JSON'
        )
        assert response.status_code == 400
        assert response.json()['error'] == 'BAD_REQUEST'

    def test_create_product_fails_with_invalid_data(
        self, gateway_service, web_session
    ):
        response = web_session.post(
            '/products',
            json.dumps({"id": 1})
        )
        assert response.status_code == 400
        assert response.json()['error'] == 'VALIDATION_ERROR'


class TestGetOrder(object):

    def test_can_get_order(self, gateway_service, web_session):
        # setup mock orders-service response:
        gateway_service.orders_rpc.get_order.return_value = {
            'id': 1,
            'order_details': [
                {
                    'id': 1,
                    'quantity': 2,
                    'product_id': 'the_odyssey',
                    'price': '200.00'
                },
                {
                    'id': 2,
                    'quantity': 1,
                    'product_id': 'the_enigma',
                    'price': '400.00'
                }
            ]
        }

        # setup mock products-service response:
        gateway_service.products_rpc.list.return_value = [
            {
                'id': 'the_odyssey',
                'title': 'The Odyssey',
                'maximum_speed': 3,
                'in_stock': 899,
                'passenger_capacity': 100
            },
            {
                'id': 'the_enigma',
                'title': 'The Enigma',
                'maximum_speed': 200,
                'in_stock': 1,
                'passenger_capacity': 4
            },
        ]

        # call the gateway service to get order #1
        response = web_session.get('/orders/1')
        assert response.status_code == 200

        expected_response = {
            'id': 1,
            'order_details': [
                {
                    'id': 1,
                    'quantity': 2,
                    'product_id': 'the_odyssey',
                    'image':
                        'http://example.com/airship/images/the_odyssey.jpg',
                    'product': {
                        'id': 'the_odyssey',
                        'title': 'The Odyssey',
                        'maximum_speed': 3,
                        'in_stock': 899,
                        'passenger_capacity': 100
                    },
                    'price': '200.00'
                },
                {
                    'id': 2,
                    'quantity': 1,
                    'product_id': 'the_enigma',
                    'image':
                        'http://example.com/airship/images/the_enigma.jpg',
                    'product': {
                        'id': 'the_enigma',
                        'title': 'The Enigma',
                        'maximum_speed': 200,
                        'in_stock': 1,
                        'passenger_capacity': 4
                    },
                    'price': '400.00'
                }
            ]
        }
        assert expected_response == response.json()

        # check dependencies called as expected
        assert [call(1)] == gateway_service.orders_rpc.get_order.call_args_list
        assert [call()] == gateway_service.products_rpc.list.call_args_list

    def test_order_not_found(self, gateway_service, web_session):
        gateway_service.orders_rpc.get_order.side_effect = (
            OrderNotFound('missing'))

        # call the gateway service to get order #1
        response = web_session.get('/orders/1')
        assert response.status_code == 404
        payload = response.json()
        assert payload['error'] == 'ORDER_NOT_FOUND'
        assert payload['message'] == 'missing'


class TestCreateOrder(object):

    def test_can_create_order(self, gateway_service, web_session):
        # setup mock products-service response:
        gateway_service.products_rpc.list.return_value = [
            {
                'id': 'the_odyssey',
                'title': 'The Odyssey',
                'maximum_speed': 3,
                'in_stock': 899,
                'passenger_capacity': 100
            },
            {
                'id': 'the_enigma',
                'title': 'The Enigma',
                'maximum_speed': 200,
                'in_stock': 1,
                'passenger_capacity': 4
            },
        ]

        # setup mock create response
        gateway_service.orders_rpc.create_order.return_value = {
            'id': 11,
            'order_details': []
        }

        # call the gateway service to create the order
        response = web_session.post(
            '/orders',
            json.dumps({
                'order_details': [
                    {
                        'product_id': 'the_odyssey',
                        'price': '41.00',
                        'quantity': 3
                    }
                ]
            })
        )
        assert response.status_code == 200
        assert response.json() == {'id': 11}
        assert gateway_service.products_rpc.list.call_args_list == [call()]
        assert gateway_service.orders_rpc.create_order.call_args_list == [
            call([
                {'product_id': 'the_odyssey', 'quantity': 3, 'price': '41.00'}
            ])
        ]

    def test_create_order_fails_with_invalid_json(
        self, gateway_service, web_session
    ):
        # call the gateway service to create the order
        response = web_session.post(
            '/orders', 'NOT-JSON'
        )
        assert response.status_code == 400
        assert response.json()['error'] == 'BAD_REQUEST'

    def test_create_order_fails_with_invalid_data(
        self, gateway_service, web_session
    ):
        # call the gateway service to create the order
        response = web_session.post(
            '/orders',
            json.dumps({
                'order_details': [
                    {
                        'product_id': 'the_odyssey',
                        'price': '41.00',
                    }
                ]
            })
        )
        assert response.status_code == 400
        assert response.json()['error'] == 'VALIDATION_ERROR'

    def test_create_order_fails_with_unknown_product(
        self, gateway_service, web_session
    ):
        # setup mock products-service response:
        gateway_service.products_rpc.list.return_value = [
            {
                'id': 'the_odyssey',
                'title': 'The Odyssey',
                'maximum_speed': 3,
                'in_stock': 899,
                'passenger_capacity': 100
            },
            {
                'id': 'the_enigma',
                'title': 'The Enigma',
                'maximum_speed': 200,
                'in_stock': 1,
                'passenger_capacity': 4
            },
        ]

        # call the gateway service to create the order
        response = web_session.post(
            '/orders',
            json.dumps({
                'order_details': [
                    {
                        'product_id': 'unknown',
                        'price': '41',
                        'quantity': 1
                    }
                ]
            })
        )
        assert response.status_code == 404
        assert response.json()['error'] == 'PRODUCT_NOT_FOUND'
        assert response.json()['message'] == 'Product Id unknown'
