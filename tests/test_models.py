import os
import logging
import unittest
from decimal import Decimal

from service.models import Product, Category, db
from service import app
from tests.factories import ProductFactory, CategoryFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


class TestProductModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        db.session.close()

    def setUp(self):
        db.session.query(Product).delete()
        db.session.query(Category).delete()  # Ensure categories are also cleaned
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    def test_create_a_product(self):
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertIsNotNone(product)
        self.assertIsNone(product.id)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertTrue(product.available)
        self.assertEqual(product.price, Decimal('12.50'))
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        self.assertEqual(Product.all(), [])
        
        # Create a category first since Product has a foreign key to Category
        category = CategoryFactory()
        category.create()

        product = ProductFactory(category=category) # Link product to the created category
        product.id = None
        product.create()

        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)

        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(new_product.price, product.price) # Compare Decimals directly
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    def test_read_a_product(self):
        category = CategoryFactory()
        category.create()
        product = ProductFactory(category=category)
        product.create()

        found_product = Product.find(product.id)
        self.assertIsNotNone(found_product)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.price, product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_a_product(self):
        category = CategoryFactory()
        category.create()
        product = ProductFactory(category=category)
        product.create()

        product.description = "Updated description"
        product.update()

        found_product = Product.find(product.id)
        self.assertEqual(found_product.description, "Updated description")

    def test_delete_a_product(self):
        category = CategoryFactory()
        category.create()
        product = ProductFactory(category=category)
        product.create()
        self.assertEqual(len(Product.all()), 1)

        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        self.assertEqual(len(Product.all()), 0)
        
        category1 = CategoryFactory()
        category1.create()
        category2 = CategoryFactory()
        category2.create()

        ProductFactory(category=category1).create()
        ProductFactory(category=category2).create()
        ProductFactory(category=category1).create()

        self.assertEqual(len(Product.all()), 3)

    def test_find_by_name(self):
        category = CategoryFactory()
        category.create()
        ProductFactory(name="Keyboard", category=category).create()
        ProductFactory(name="Mouse", category=category).create()
        ProductFactory(name="Keyboard", category=category).create()

        products = Product.find_by_name("Keyboard")
        self.assertEqual(len(products), 2)
        for product in products:
            self.assertEqual(product.name, "Keyboard")

    def test_find_by_availability(self):
        category = CategoryFactory()
        category.create()
        ProductFactory(available=True, category=category).create()
        ProductFactory(available=False, category=category).create()
        ProductFactory(available=True, category=category).create()

        products = Product.find_by_availability(True)
        self.assertEqual(len(products), 2)
        for product in products:
            self.assertTrue(product.available)

    def test_find_by_category(self):
        category_tech = CategoryFactory(name="Tech")
        category_tech.create()
        category_food = CategoryFactory(name="Food")
        category_food.create()

        ProductFactory(category=category_tech).create()
        ProductFactory(category=category_food).create()
        ProductFactory(category=category_tech).create()

        products = Product.find_by_category(category_tech)
        self.assertEqual(len(products), 2)
        for product in products:
            self.assertEqual(product.category.name, "Tech")

    def test_deserialize_a_product(self):
        category = CategoryFactory()
        category.create()
        product = ProductFactory(category=category)
        
        data = {
            "id": 1,
            "name": "Test Product",
            "description": "This is a test description",
            "price": 99.99,
            "available": True,
            "category_id": category.id # Use category_id as expected by deserialize
        }
        
        product.deserialize(data)
        self.assertEqual(product.id, 1)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.description, "This is a test description")
        self.assertEqual(product.price, Decimal('99.99'))
        self.assertEqual(product.available, True)
        self.assertEqual(product.category_id, category.id) # Check category_id

    def test_deserialize_missing_data(self):
        product = Product()
        with self.assertRaises(AttributeError):
            product.deserialize({"name": "Test"})

    def test_deserialize_invalid_data(self):
        product = Product()
        with self.assertRaises(TypeError):
            product.deserialize("this is not a dictionary")

    def test_serialize_a_product(self):
        category = CategoryFactory()
        category.create()
        product = ProductFactory(category=category)
        product.create() # Ensure ID and category are set

        data = product.serialize()
        self.assertIn("id", data)
        self.assertEqual(data["id"], product.id)
        self.assertEqual(data["name"], product.name)
        self.assertEqual(data["description"], product.description)
        self.assertEqual(data["price"], str(product.price)) # Price is often stringified
        self.assertEqual(data["available"], product.available)
        self.assertEqual(data["category_id"], product.category.id) # category_id for serialization
