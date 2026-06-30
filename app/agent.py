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

# Flower shop product catalog
PRODUCTS = {
    "bouquet_roses": {"title": "Bouquet of Red Roses", "price": 35.00},
    "pot_ceramic": {"title": "Ceramic Pot", "price": 15.00},
    "bouquet_sunflowers": {"title": "Sunflower Bundle", "price": 25.00},
    "bouquet_tulips": {"title": "Spring Tulips", "price": 30.00},
    "orchid_white": {"title": "White Orchid", "price": 45.00},
    "gardenias": {"title": "Gardenias", "price": 20.00},
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
        res += f"- [ID: {pid}] {info['title']} - ${info['price']:.2f}\n"
    return res


def discover_payment_methods() -> str:
    """Discover supported payment handlers for checkout."""
    return "Supported Payment Handlers:\n- ID: mock_payment_handler (Name: Mock Payment Handler)"


def create_checkout_session(
    tool_context: ToolContext,
    product_id: str,
    quantity: int = 1,
    buyer_name: str = "John Doe",
    buyer_email: str = "john.doe@example.com",
) -> str:
    """Initialize a new checkout session with the first product and buyer info.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID of the first product to add.
        quantity: The quantity of the product to add. Defaults to 1.
        buyer_name: Full name of the buyer. Defaults to "John Doe".
        buyer_email: Email address of the buyer. Defaults to "john.doe@example.com".
    """
    if product_id not in PRODUCTS:
        return f"Error: Product '{product_id}' not found."

    checkout_id = f"CHK-{random.randint(100000, 999999)}"
    tool_context.state["checkout_id"] = checkout_id
    tool_context.state["cart"] = {product_id: quantity}
    tool_context.state["buyer"] = {"name": buyer_name, "email": buyer_email}

    total = PRODUCTS[product_id]["price"] * quantity
    return f"Checkout session created successfully.\n- Checkout ID: {checkout_id}\n- Item: {PRODUCTS[product_id]['title']} (x{quantity})\n- Total: ${total:.2f}"


def add_item_to_checkout(
    tool_context: ToolContext, product_id: str, quantity: int = 1
) -> str:
    """Add additional items to the active checkout session.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID of the product to add.
        quantity: The quantity of the product to add. Defaults to 1.
    """
    if "checkout_id" not in tool_context.state:
        return "Error: No active checkout session. Please create one first."
    if product_id not in PRODUCTS:
        return f"Error: Product '{product_id}' not found."

    cart = tool_context.state["cart"]
    cart[product_id] = cart.get(product_id, 0) + quantity
    tool_context.state["cart"] = cart

    subtotal = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())
    return f"Item added successfully. Current Subtotal: ${subtotal:.2f}"


def apply_discount_code(tool_context: ToolContext, code: str) -> str:
    """Apply a discount code to the current checkout session.

    Args:
        tool_context: The tool context containing session state.
        code: The discount code to apply.
    """
    if "checkout_id" not in tool_context.state:
        return "Error: No active checkout session."

    tool_context.state["discount_code"] = code
    cart = tool_context.state["cart"]
    subtotal = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())

    discount_amount = 0.0
    if code == "10OFF":
        discount_amount = subtotal * 0.10

    total = subtotal - discount_amount
    return f"Discount code '{code}' applied.\n- Discount: -${discount_amount:.2f}\n- Total: ${total:.2f}"


def select_fulfillment_destination(
    tool_context: ToolContext, street_address: str, postal_code: str
) -> str:
    """Set the shipping address and retrieve available shipping options.

    Args:
        tool_context: The tool context containing session state.
        street_address: The delivery street address.
        postal_code: The postal code.
    """
    if "checkout_id" not in tool_context.state:
        return "Error: No active checkout session."

    tool_context.state["shipping_address"] = {
        "address": street_address,
        "zip": postal_code,
    }

    return (
        f"Fulfillment destination set to: {street_address} (Zip: {postal_code})\n"
        f"Available Options:\n"
        f"- ID: opt_standard (Name: Standard Shipping - $5.00)\n"
        f"- ID: opt_express (Name: Express Shipping - $15.00)"
    )


def select_fulfillment_option(tool_context: ToolContext, option_id: str) -> str:
    """Select the preferred shipping option.

    Args:
        tool_context: The tool context containing session state.
        option_id: The ID of the preferred shipping option (e.g. opt_standard).
    """
    if "checkout_id" not in tool_context.state:
        return "Error: No active checkout session."

    shipping_fee = 5.00 if option_id == "opt_standard" else 15.00
    tool_context.state["shipping_fee"] = shipping_fee
    tool_context.state["shipping_option"] = option_id

    cart = tool_context.state["cart"]
    subtotal = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())
    discount = (
        subtotal * 0.10 if tool_context.state.get("discount_code") == "10OFF" else 0.0
    )

    total = subtotal - discount + shipping_fee
    return f"Fulfillment option selected: {option_id} (${shipping_fee:.2f}).\n- Grand Total: ${total:.2f}"


def complete_payment(
    tool_context: ToolContext, handler_id: str = "mock_payment_handler"
) -> str:
    """Process the payment using mock_payment_handler and finalize the order.

    Args:
        tool_context: The tool context containing session state.
        handler_id: The ID of the payment handler to use. Defaults to "mock_payment_handler".
    """
    if "checkout_id" not in tool_context.state:
        return "Error: No active checkout session."
    if "shipping_fee" not in tool_context.state:
        return "Error: Please select shipping options before completing payment."

    order_id = f"ORD-{random.randint(10000, 99999)}"
    cart = tool_context.state["cart"]
    buyer = tool_context.state["buyer"]
    addr = tool_context.state["shipping_address"]

    subtotal = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())
    discount = (
        subtotal * 0.10 if tool_context.state.get("discount_code") == "10OFF" else 0.0
    )
    shipping_fee = tool_context.state["shipping_fee"]
    total = subtotal - discount + shipping_fee

    res = f"🎉 Order finalized successfully via {handler_id}!\n"
    res += f"- Order ID: {order_id}\n"
    res += f"- Total Paid: ${total:.2f}\n"
    res += f"- Shipping to: {addr['address']} (Zip: {addr['zip']})\n"
    res += f"- Receipt sent to: {buyer['email']}"

    # 状態の初期化
    tool_context.state["cart"] = {}
    tool_context.state["checkout_id"] = None
    tool_context.state["discount_code"] = None
    tool_context.state["shipping_address"] = None
    tool_context.state["shipping_fee"] = None
    tool_context.state["shipping_option"] = None
    return res


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful shopping assistant for the UCP Flower Shop. "
        "Your goal is to guide the user through their shopping journey by coordinating the checkout process:\n"
        "1. List or search available products using 'search_products'.\n"
        "2. Discover supported payment methods using 'discover_payment_methods'.\n"
        "3. Start a new checkout session with a product using 'create_checkout_session'.\n"
        "4. Add more items to the checkout using 'add_item_to_checkout'.\n"
        "5. Apply discount codes (like '10OFF') using 'apply_discount_code'.\n"
        "6. Set shipping destination details using 'select_fulfillment_destination'.\n"
        "7. Choose a shipping option (like standard or express) using 'select_fulfillment_option'.\n"
        "8. Finalize the checkout and complete payment using 'complete_payment'."
    ),
    tools=[
        search_products,
        discover_payment_methods,
        create_checkout_session,
        add_item_to_checkout,
        apply_discount_code,
        select_fulfillment_destination,
        select_fulfillment_option,
        complete_payment,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
