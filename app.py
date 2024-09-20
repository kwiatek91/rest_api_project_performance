from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger, swag_from
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajny_klucz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:password@db:3306/database_name'
app.config['JWT_SECRET_KEY'] = 'jwt_tajny_klucz'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Swagger Configuration
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "E-commerce API",
        "description": "API documentation for the E-commerce application",
        "version": "1.0"
    },
    "basePath": "/",
    "schemes": ["http", "https"],
}
swagger = Swagger(app, template=swagger_template)

api = Api(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Stored in plain text (not secure)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    price = db.Column(db.Float)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    products = db.Column(db.Text)  # Store product IDs as a comma-separated string

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    products = db.Column(db.Text)  # Store product IDs as a comma-separated string
    total_price = db.Column(db.Float)

# Functions to create random products and users
def create_random_products(num_products=10):
    products = []
    for i in range(1, num_products + 1):
        name = f'product_{i}'
        price = round(random.uniform(5.0, 100.0), 2)
        product = Product(name=name, price=price)
        products.append(product)
    return products

def create_users(num_users=1000, password='password'):
    users = []
    # Add the admin user
    admin_user = User(username='admin', password='admin')
    users.append(admin_user)
    
    # Create regular users
    for i in range(1, num_users + 1):
        username = f'user{i}'
        user = User(username=username, password=password)
        users.append(user)
    return users

# Initialize database and add random products and users before first request
@app.before_first_request
def initialize_database():
    db.create_all()

    # Add random products if none exist
    if not Product.query.first():
        products = create_random_products()
        db.session.add_all(products)
        db.session.commit()
        print(f"Added {len(products)} random products to the database.")
    else:
        print("Products already exist in the database. No new products added.")

    # Add users if none exist
    if not User.query.first():
        users = create_users()
        db.session.add_all(users)
        db.session.commit()
        print(f"Added {len(users)} users to the database with password 'password' (except 'admin' user who uses 'admin' as password).")
        for user in users:
            print(f"Username: {user.username}")
    else:
        print("Users already exist in the database. No new users added.")

# Endpoints
class Login(Resource):
    @swag_from({
        'tags': ['Authentication'],
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {'type': 'string'},
                        'password': {'type': 'string'}
                    },
                    'required': ['username', 'password']
                }
            }
        ],
        'responses': {
            200: {
                'description': 'Successful login',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'access_token': {'type': 'string'}
                    }
                }
            },
            401: {
                'description': 'Invalid login credentials'
            }
        }
    })
    def post(self):
        """
        User login
        ---
        """
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            access_token = create_access_token(identity=user.id)
            return {'access_token': access_token}, 200
        else:
            return {'message': 'Invalid login credentials'}, 401

class ProductResource(Resource):
    @jwt_required()
    @swag_from({
        'tags': ['Products'],
        'parameters': [
            {
                'name': 'product_id',
                'in': 'path',
                'type': 'integer',
                'required': True,
                'description': 'ID of the product'
            }
        ],
        'responses': {
            200: {
                'description': 'Product details',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer'},
                        'name': {'type': 'string'},
                        'price': {'type': 'number'}
                    }
                }
            },
            404: {
                'description': 'Product not found'
            }
        }
    })
    def get(self, product_id):
        """
        Get product details
        ---
        """
        product = Product.query.get(product_id)
        if product:
            return {'id': product.id, 'name': product.name, 'price': product.price}
        else:
            return {'message': 'Product not found'}, 404

class ProductList(Resource):
    @jwt_required()
    @swag_from({
        'tags': ['Products'],
        'responses': {
            200: {
                'description': 'List of products',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'name': {'type': 'string'},
                            'price': {'type': 'number'}
                        }
                    }
                }
            }
        }
    })
    def get(self):
        """
        Get list of products
        ---
        """
        products = Product.query.all()
        return [{'id': p.id, 'name': p.name, 'price': p.price} for p in products]

class AddToCart(Resource):
    @jwt_required()
    @swag_from({
        'tags': ['Cart'],
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'product_id': {'type': 'integer'}
                    },
                    'required': ['product_id']
                }
            }
        ],
        'responses': {
            200: {
                'description': 'Product added to cart',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'},
                        'cart_id': {'type': 'integer'}
                    }
                }
            },
            404: {
                'description': 'User or product not found'
            }
        }
    })
    def post(self):
        """
        Add product to cart
        ---
        """
        data = request.get_json()
        product_id = data.get('product_id')
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'message': 'User not found'}, 404

        product = Product.query.get(product_id)
        if not product:
            return {'message': 'Product not found'}, 404

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id, products=str(product_id))
            db.session.add(cart)
        else:
            product_ids = cart.products.split(',')
            product_ids.append(str(product_id))
            cart.products = ','.join(product_ids)

        db.session.commit()
        return {'message': 'Product added to cart', 'cart_id': cart.id}, 200

class FinalizeOrder(Resource):
    @jwt_required()
    @swag_from({
        'tags': ['Order'],
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'cart_id': {'type': 'integer'}
                    },
                    'required': ['cart_id']
                }
            }
        ],
        'responses': {
            200: {
                'description': 'Order placed successfully',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'},
                        'order_id': {'type': 'integer'},
                        'total_price': {'type': 'number'}
                    }
                }
            },
            400: {
                'description': 'Cart is empty or not found'
            },
            404: {
                'description': 'User not found'
            }
        }
    })
    def post(self):
        """
        Finalize order
        ---
        """
        data = request.get_json()
        cart_id = data.get('cart_id')
        if not cart_id:
            return {'message': 'Cart ID is required'}, 400

        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'message': 'User not found'}, 404

        cart = Cart.query.filter_by(id=cart_id, user_id=user_id).first()
        if not cart or not cart.products:
            return {'message': 'Cart is empty or not found. Cannot finalize order.'}, 400

        product_ids = [int(pid) for pid in cart.products.split(',')]
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        total_price = sum(p.price for p in products)

        order = Order(user_id=user_id, products=cart.products, total_price=total_price)
        db.session.add(order)

        # Clear the cart
        db.session.delete(cart)

        db.session.commit()
        return {
            'message': 'Order placed successfully',
            'order_id': order.id,
            'total_price': total_price
        }, 200

class AdminOrderList(Resource):
    @jwt_required()
    @swag_from({
        'tags': ['Admin'],
        'responses': {
            200: {
                'description': 'List of all orders',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'order_id': {'type': 'integer'},
                            'user': {'type': 'string'},
                            'products': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'integer'},
                                        'name': {'type': 'string'},
                                        'price': {'type': 'number'}
                                    }
                                }
                            },
                            'total_price': {'type': 'number'}
                        }
                    }
                }
            },
            403: {
                'description': 'Access denied'
            }
        }
    })
    def get(self):
        """
        Get list of all orders (admin only)
        ---
        """
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user.username != 'admin':
            return {'message': 'Access denied'}, 403

        orders = Order.query.all()
        order_list = []
        for order in orders:
            # Get user who placed the order
            order_user = User.query.get(order.user_id)
            username = order_user.username if order_user else 'Unknown'

            # Get products in the order
            product_ids = [int(pid) for pid in order.products.split(',')]
            products = Product.query.filter(Product.id.in_(product_ids)).all()
            product_details = [{'id': p.id, 'name': p.name, 'price': p.price} for p in products]

            order_info = {
                'order_id': order.id,
                'user': username,
                'products': product_details,
                'total_price': order.total_price
            }
            order_list.append(order_info)
        return order_list, 200

# Registration of endpoints
api.add_resource(Login, '/login')
api.add_resource(ProductResource, '/products/<int:product_id>')
api.add_resource(ProductList, '/products')
api.add_resource(AddToCart, '/cart')
api.add_resource(FinalizeOrder, '/order')
api.add_resource(AdminOrderList, '/admin/orders')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
