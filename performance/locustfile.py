import random
from locust import HttpUser, TaskSet, task, between

# Set the maximum acceptable response time in milliseconds
MAX_RESPONSE_TIME = 1000  # 1 second

class EcommerceTasks(TaskSet):
    def on_start(self):
        user_number = random.randint(1, 1000)
        username = f"user{user_number}"
        password = "password"
        response = self.client.post("/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            self.token = None
            print(f"Failed to log in as {username}")

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(10)
    def browse_products(self):
        with self.client.get("/products", headers=self.get_headers(), name="Browse Products", catch_response=True) as response:
            response_time_ms = response.elapsed.total_seconds() * 1000
            if response.status_code != 200:
                response.failure(f"Received unexpected status code {response.status_code}")
            elif response_time_ms > MAX_RESPONSE_TIME:
                response.failure(f"Response time exceeded {MAX_RESPONSE_TIME} ms")
            else:
                try:
                    self.products = response.json()
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse JSON response: {e}")

    @task(5)
    def view_product(self):
        if hasattr(self, 'products') and self.products:
            product = random.choice(self.products)
            product_id = product["id"]
            with self.client.get(f"/products/{product_id}", headers=self.get_headers(), name="View Product Details", catch_response=True) as response:
                response_time_ms = response.elapsed.total_seconds() * 1000
                if response.status_code != 200:
                    response.failure(f"Received unexpected status code {response.status_code}")
                elif response_time_ms > MAX_RESPONSE_TIME:
                    response.failure(f"Response time exceeded {MAX_RESPONSE_TIME} ms")
                else:
                    response.success()


    @task(3)
    def add_to_cart(self):
        if hasattr(self, 'products') and self.products:
            product = random.choice(self.products)
            product_id = product["id"]
            with self.client.post("/cart",
                                  json={"product_id": product_id},
                                  headers=self.get_headers(),
                                  name="Add to Cart",
                                  catch_response=True) as response:
                response_time_ms = response.elapsed.total_seconds() * 1000
                if response.status_code != 200:
                    response.failure(f"Received unexpected status code {response.status_code}")
                elif response_time_ms > MAX_RESPONSE_TIME:
                    response.failure(f"Response time exceeded {MAX_RESPONSE_TIME} ms")
                else:
                    try:
                        self.cart_id = response.json().get("cart_id")
                        if self.cart_id:
                            response.success()
                        else:
                            response.failure("No cart_id in response")
                    except Exception as e:
                        response.failure(f"Failed to parse JSON response: {e}")


    @task(2)
    def finalize_order(self):
        if hasattr(self, 'cart_id') and self.cart_id:
            with self.client.post("/order",
                                  json={"cart_id": self.cart_id},
                                  headers=self.get_headers(),
                                  name="Finalize Order",
                                  catch_response=True) as response:
                response_time_ms = response.elapsed.total_seconds() * 1000
                if response.status_code != 200:
                    response.failure(f"Received unexpected status code {response.status_code}")
                elif response_time_ms > MAX_RESPONSE_TIME:
                    response.failure(f"Response time exceeded {MAX_RESPONSE_TIME} ms")
                else:
                    # Order placed successfully, reset cart_id
                    self.cart_id = None
                    response.success()
 

class EcommerceUser(HttpUser):
    tasks = [EcommerceTasks]
    wait_time = between(1, 5)