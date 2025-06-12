from flask import jsonify, request, abort, url_for
from service.models import Product, Category
from service.common import status
from . import app


@app.route("/health")
def healthcheck():
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


@app.route("/")
def index():
    return app.send_static_file("index.html")


def check_content_type(content_type):
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


@app.route("/products", methods=["POST"])
def create_products():
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    try:
        product.deserialize(data)
    except AttributeError as error:
        app.logger.error("Bad Request: %s", error)
        abort(status.HTTP_400_BAD_REQUEST, str(error))
    except TypeError as error:
        app.logger.error("Bad Request: %s", error)
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()
    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


@app.route("/products", methods=["GET"])
def list_products():
    app.logger.info("Request to list Products...")
    products = []
    name = request.args.get("name")
    category = request.args.get("category")
    available = request.args.get("available")

    if name:
        app.logger.info("Find by name: %s", name)
        products = Product.find_by_name(name)
    elif category:
        app.logger.info("Find by category: %s", category)
        try:
            category_obj = Category.find_by_name(category)
            if not category_obj:
                app.logger.info("Category %s not found for filtering", category)
                return jsonify([]), status.HTTP_200_OK
            products = Product.find_by_category(category_obj)
        except Exception as e:
            app.logger.error("Invalid category type: %s", e)
            abort(status.HTTP_400_BAD_REQUEST, f"Invalid category: {category}")
    elif available:
        app.logger.info("Find by availability: %s", available)
        is_available = available.lower() == "true"
        products = Product.find_by_availability(is_available)
    else:
        app.logger.info("Find all")
        products = Product.all()

    results = [product.serialize() for product in products]
    app.logger.info("Returning %d products", len(results))
    return jsonify(results), status.HTTP_200_OK


@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id):
    app.logger.info("Request to Retrieve Product with id [%s]", product_id)
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id '{product_id}' was not found.")
    return jsonify(product.serialize()), status.HTTP_200_OK


@app.route("/products/<int:product_id>", methods=["PUT"])
def update_products(product_id):
    app.logger.info("Request to Update Product with id [%s]", product_id)
    check_content_type("application/json")

    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id '{product_id}' was not found.")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    try:
        product.deserialize(data)
    except AttributeError as error:
        app.logger.error("Bad Request: %s", error)
        abort(status.HTTP_400_BAD_REQUEST, str(error))
    except TypeError as error:
        app.logger.error("Bad Request: %s", error)
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    product.id = product_id
    product.update()
    app.logger.info("Product with id [%s] updated!", product.id)

    return jsonify(product.serialize()), status.HTTP_200_OK


@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    app.logger.info("Request to Delete Product with id [%s]", product_id)
    product = Product.find(product_id)
    if product:
        product.delete()
        app.logger.info("Product with id [%s] deleted!", product_id)
    return "", status.HTTP_204_NO_CONTENT
