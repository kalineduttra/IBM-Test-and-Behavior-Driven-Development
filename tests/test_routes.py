import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory, CategoryFactory


DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


class TestProductRoutes(TestCase):
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    def tearDownClass(cls):
        db.session.close()

    def setUp(self):
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.query(Category).delete()
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    def _create_products(self, count: int = 1) -> list:
        products = []
        categories = [CategoryFactory().create() for _ in range(count)]
        for i in range(count):
            test_product = ProductFactory(category=categories[i % len(categories)])
            test_product.create()
            products.append(test_product)
        return products

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    def test_create_product(self):
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category_id"], test_product.category.id)

        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category_id"], test_product.category.id)

    def test_create_product_with_no_name(self):
        product = self._create_products()[0]
        new_product_data = product.serialize()
        del new_product_data["name"]
        response = self.client.post(BASE_URL, json=new_product_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)

    def test_get_product_not_found(self):
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        test_product = self._create_products(1)[0]
        new_description = "Updated product description"
        test_product.description = new_description
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["description"], new_description)

    def test_update_product_not_found(self):
        product_data = ProductFactory().serialize()
        response = self.client.put(f"{BASE_URL}/0", json=product_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_no_content_type(self):
        test_product = self._create_products(1)[0]
        response = self.client.put(f"{BASE_URL}/{test_product.id}", data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_product_wrong_content_type(self):
        test_product = self._create_products(1)[0]
        response = self.client.put(f"{BASE_URL}/{test_product.id}", data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_product(self):
        test_product = self._create_products(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        resp = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_all_products(self):
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_query_product_list_by_name(self):
        products = self._create_products(5)
        test_name = products[0].name
        count = len([product for product in products if product.name == test_name])
        response = self.client.get(BASE_URL, query_string=f"name={test_name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_query_product_list_by_availability(self):
        self._create_products(10)
        available_products = [product for product in Product.all() if product.available is True]
        count = len(available_products)
        response = self.client.get(BASE_URL, query_string="available=True")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["available"], True)

    def test_query_product_list_by_category(self):
        self._create_products(10)
        test_category = Product.all()[0].category.name
        count = len([product for product in Product.all() if product.category.name == test_category])
        response = self.client.get(BASE_URL, query_string=f"category={test_category}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["category_id"], Product.find_by_name(product["name"])[0].category.id)
