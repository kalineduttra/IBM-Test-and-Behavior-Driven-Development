import factory
from factory.fuzzy import FuzzyDecimal
from service.models import Product, Category


class CategoryFactory(factory.Factory):
    class Meta:
        model = Category

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker('word')


class ProductFactory(factory.Factory):
    class Meta:
        model = Product

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('paragraph', nb_sentences=5)
    price = FuzzyDecimal(1.00, 1000.00, 2)
    available = factory.Faker('boolean')
    category = factory.SubFactory(CategoryFactory)
