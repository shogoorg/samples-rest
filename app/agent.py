# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


import random
from google.adk.tools.tool_context import ToolContext

# Flower shop product catalog (aligned with products.csv in test data)
PRODUCTS = {
    "bouquet_roses": {"title": "Bouquet of Red Roses", "price": 3500},
    "pot_ceramic": {"title": "Ceramic Pot", "price": 1500},
    "bouquet_sunflowers": {"title": "Sunflower Bundle", "price": 2500},
    "bouquet_tulips": {"title": "Spring Tulips", "price": 3000},
    "orchid_white": {"title": "White Orchid", "price": 4500},
    "gardenias": {"title": "Gardenias", "price": 2000},
}


def search_products(query: str) -> str:
    """Search for flowers or products available in the flower shop catalog.

    Args:
        query: The search term (e.g. roses, sunflowers, pot, tulips, orchid).
    """
    query_lower = query.lower()
    matches = [
        (pid, info)
        for pid, info in PRODUCTS.items()
        if query_lower in pid or query_lower in info["title"].lower()
    ]
    if not matches:
        return f"No products found matching '{query}'."

    res = "Available Products in Stock:\n"
    for pid, info in matches:
        res += f"- [ID: {pid}] {info['title']} - ¥{info['price']}\n"
    return res


def add_to_checkout(
    tool_context: ToolContext, product_id: str, quantity: int = 1
) -> str:
    """Add a product to the user's checkout session.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID of the product to add (e.g., bouquet_roses).
        quantity: The quantity of the product to add. Defaults to 1.
    """
    if product_id not in PRODUCTS:
        return f"Error: Product ID '{product_id}' does not exist. Please search for valid products first."

    # Initialize cart state if not exists
    if "cart" not in tool_context.state:
        tool_context.state["cart"] = {}

    cart = tool_context.state["cart"]
    cart[product_id] = cart.get(product_id, 0) + quantity

    # Create current cart summary
    summary = "Current Cart Summary:\n"
    total = 0
    for pid, qty in cart.items():
        pinfo = PRODUCTS[pid]
        subtotal = pinfo["price"] * qty
        total += subtotal
        summary += f"- {pinfo['title']} (x{qty}) - ¥{subtotal}\n"
    summary += f"Total Amount: ¥{total}\n\n"

    # Check if delivery details are provided
    cust_info = tool_context.state.get("customer_info")
    if not cust_info:
        summary += (
            "To complete the checkout, please provide your email address, "
            "shipping address, and postal code so we can set up your delivery."
        )
    else:
        summary += "All details are set. You can now complete your purchase by running 'complete_payment'."

    return summary


def set_customer_info(
    tool_context: ToolContext, email: str, street_address: str, postal_code: str
) -> str:
    """Save customer delivery details and email for the current checkout session.

    Args:
        tool_context: The tool context containing session state.
        email: The customer's email address.
        street_address: The shipping address.
        postal_code: The postal code.
    """
    tool_context.state["customer_info"] = {
        "email": email,
        "street_address": street_address,
        "postal_code": postal_code,
    }

    cart = tool_context.state.get("cart", {})
    if not cart:
        return "Customer information saved successfully. Please add products to your checkout next."

    total = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())

    res = "Customer Details Updated:\n"
    res += f"- Email: {email}\n"
    res += f"- Shipping: {street_address} (Zip: {postal_code})\n\n"
    res += f"Order Total: ¥{total}\n"
    res += "Everything is ready! Please run 'complete_payment' to finish your purchase."
    return res


def complete_payment(tool_context: ToolContext) -> str:
    """Process the payment and complete the checkout session.

    Args:
        tool_context: The tool context containing session state.
    """
    cart = tool_context.state.get("cart", {})
    cust_info = tool_context.state.get("customer_info")

    if not cart:
        return "Cannot complete payment: Your cart is empty."
    if not cust_info:
        return "Cannot complete payment: Shipping details and email are required. Please provide them first."

    # Simulate payment completion
    order_id = f"ORD-{random.randint(10000, 99999)}"
    total = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())

    res = f"🎉 Payment Completed and Order Created successfully!\n"
    res += f"Order ID: {order_id}\n"
    res += f"Total Paid: ¥{total}\n"
    res += f"Receipt Sent To: {cust_info['email']}\n"
    res += f"Deliver To: {cust_info['street_address']} (Zip: {cust_info['postal_code']})\n\n"
    res += "Thank you for shopping at the UCP Flower Shop!"

    # Reset session state
    tool_context.state["cart"] = {}
    tool_context.state["customer_info"] = None

    return res


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful shopping assistant for the UCP Flower Shop. "
        "Your goal is to guide the user through their shopping journey:\n"
        "1. Help them search for products using 'search_products'.\n"
        "2. Add their selected items to checkout using 'add_to_checkout'.\n"
        "3. Ask the user for their email, shipping address, and postal code, then save it using 'set_customer_info'.\n"
        "4. Finalize the order using 'complete_payment' once details are filled."
    ),
    tools=[search_products, add_to_checkout, set_customer_info, complete_payment],
)

app = App(
    root_agent=root_agent,
    name="app",
)
