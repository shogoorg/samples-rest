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


import httpx
import sqlite3
import random
import uuid
from google.adk.tools.tool_context import ToolContext

SERVER_URL = "http://localhost:8182"
PRODUCTS_DB_PATH = "/tmp/ucp_test/products.db"

def get_ucp_headers() -> dict[str, str]:
    """Generate required headers for UCP API calls."""
    return {
        "UCP-Agent": 'profile="https://agent.example/profile"',
        "Request-Signature": "test",
        "Idempotency-Key": str(uuid.uuid4()),
        "Request-Id": str(uuid.uuid4()),
    }

def search_products(query: str) -> str:
    """Search for flowers or products available in the flower shop database.

    Args:
        query: The search term (e.g. roses, sunflowers, pot, tulips, orchid).
    """
    try:
        conn = sqlite3.connect(PRODUCTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, price FROM products WHERE id LIKE ? OR title LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"No products found matching '{query}'."

        res = "Available Products in Stock:\n"
        for row in rows:
            price_usd = row[2] / 100.0 if row[2] > 100 else row[2]
            res += f"- [ID: {row[0]}] {row[1]} - ${price_usd:.2f}\n"
        return res
    except Exception as e:
        PRODUCTS_FALLBACK = {
            "bouquet_roses": {"title": "Bouquet of Red Roses", "price": 35.00},
            "pot_ceramic": {"title": "Ceramic Pot", "price": 15.00},
            "bouquet_sunflowers": {"title": "Sunflower Bundle", "price": 25.00},
        }
        query_lower = query.lower()
        matches = [(pid, info) for pid, info in PRODUCTS_FALLBACK.items() if query_lower in pid]
        if not matches:
            return f"No products found matching '{query}' (Error: {e})."
        res = "Available Products (Fallback Mode):\n"
        for pid, info in matches:
            res += f"- [ID: {pid}] {info['title']} - ${info['price']:.2f}\n"
        return res

def discover_payment_methods() -> str:
    """Discover supported payment handlers from the UCP Merchant Server."""
    try:
        response = httpx.get(f"{SERVER_URL}/.well-known/ucp", headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        handlers_map = data.get("payment_handlers", {})
        supported_handlers = []
        for handlers_list in handlers_map.values():
            supported_handlers.extend(handlers_list)
            
        if not supported_handlers:
            return "No payment handlers supported by the merchant."
            
        return "Supported Payment Handlers:\n" + "\n".join([f"- ID: {h['id']} (Name: {h['name']})" for h in supported_handlers])
    except Exception as e:
        return f"Error connecting to server discovery endpoint: {e}"

def create_checkout_session(
    tool_context: ToolContext, product_id: str, quantity: int = 1, buyer_name: str = "John Doe", buyer_email: str = "john.doe@example.com"
) -> str:
    """Initialize a new checkout session on the UCP Merchant Server with buyer and product info.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID of the first product to add.
        quantity: The quantity of the product to add. Defaults to 1.
        buyer_name: Full name of the buyer.
        buyer_email: Email address of the buyer.
    """
    payload = {
        "currency": "USD",
        "line_items": [
            {
                "quantity": quantity,
                "item": {"id": product_id}
            }
        ],
        "payment": {
            "instruments": [],
            "selected_instrument_id": None,
            "handlers": [
                {"id": "shop_pay", "name": "Shop Pay"},
                {"id": "google_pay", "name": "Google Pay"},
                {"id": "mock_payment_handler", "name": "Mock Payment Handler"}
            ]
        },
        "buyer": {
            "full_name": buyer_name,
            "email": buyer_email
        }
    }
    try:
        response = httpx.post(f"{SERVER_URL}/checkout-sessions", json=payload, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        checkout_id = data["id"]
        tool_context.state["checkout_id"] = checkout_id
        tool_context.state["line_items"] = data.get("line_items", [])
        tool_context.state["currency"] = data.get("currency", "USD")
        tool_context.state["payment"] = data.get("payment", {})
        
        totals = data.get("totals", [])
        amount_total = totals[-1].get("amount", 0) / 100.0 if totals else 0.0
        return (
            f"Checkout session created successfully on server.\n"
            f"- Checkout ID: {checkout_id}\n"
            f"- Total: ${amount_total:.2f}\n"
            f"Please proceed with adding items, setting destination, or applying discounts."
        )
    except Exception as e:
        return f"Error creating checkout session: {e}"

def add_item_to_checkout(tool_context: ToolContext, product_id: str, quantity: int = 1) -> str:
    """Add additional items to the active checkout session on the server.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID of the product to add.
        quantity: The quantity of the product to add.
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session. Please create one first."
    
    try:
        checkout_resp = httpx.get(f"{SERVER_URL}/checkout-sessions/{checkout_id}", headers=get_ucp_headers())
        checkout_resp.raise_for_status()
        current_checkout = checkout_resp.json()
    except Exception as e:
        return f"Error fetching current checkout: {e}"

    line_items = current_checkout.get("line_items", [])
    item_found = False
    updated_line_items = []
    for li in line_items:
        item_id = li.get("item", {}).get("id")
        qty = li.get("quantity", 1)
        if item_id == product_id:
            qty += quantity
            item_found = True
        updated_line_items.append({
            "id": li.get("id"),
            "quantity": qty,
            "item": {"id": item_id}
        })
    
    if not item_found:
        updated_line_items.append({
            "id": str(uuid.uuid4()),
            "quantity": quantity,
            "item": {"id": product_id}
        })

    payload = {
        "id": checkout_id,
        "line_items": updated_line_items,
        "currency": current_checkout.get("currency", "USD"),
        "payment": current_checkout.get("payment", {})
    }
    try:
        response = httpx.put(f"{SERVER_URL}/checkout-sessions/{checkout_id}", json=payload, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        tool_context.state["line_items"] = data.get("line_items", [])
        tool_context.state["payment"] = data.get("payment", {})
        
        totals = data.get("totals", [])
        subtotal = totals[-1].get("amount", 0) / 100.0 if totals else 0.0
        return f"Item added successfully. Current Subtotal on server: ${subtotal:.2f}"
    except Exception as e:
        return f"Error updating checkout: {e}"

def apply_discount_code(tool_context: ToolContext, code: str) -> str:
    """Apply a discount code to the current checkout session on the server.

    Args:
        tool_context: The tool context containing session state.
        code: The discount code to apply (e.g. 10OFF).
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session."

    try:
        checkout_resp = httpx.get(f"{SERVER_URL}/checkout-sessions/{checkout_id}", headers=get_ucp_headers())
        checkout_resp.raise_for_status()
        current_checkout = checkout_resp.json()
    except Exception as e:
        return f"Error fetching current checkout: {e}"

    line_items = current_checkout.get("line_items", [])
    formatted_line_items = []
    for li in line_items:
        formatted_line_items.append({
            "id": li.get("id"),
            "quantity": li.get("quantity"),
            "item": {"id": li.get("item", {}).get("id")}
        })

    payload = {
        "id": checkout_id,
        "line_items": formatted_line_items,
        "currency": current_checkout.get("currency", "USD"),
        "payment": current_checkout.get("payment", {}),
        "discounts": {
            "codes": [code]
        }
    }
    try:
        response = httpx.put(f"{SERVER_URL}/checkout-sessions/{checkout_id}", json=payload, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        totals = data.get("totals", [])
        total = totals[-1].get("amount", 0) / 100.0 if totals else 0.0
        return f"Discount code '{code}' applied on server.\n- New Total: ${total:.2f}"
    except Exception as e:
        return f"Error applying discount code: {e}"

def select_fulfillment_destination(tool_context: ToolContext, street_address: str, postal_code: str) -> str:
    """Set the shipping address on the server and retrieve available shipping options.

    Args:
        tool_context: The tool context containing session state.
        street_address: The delivery street address.
        postal_code: The postal code.
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session."

    try:
        checkout_resp = httpx.get(f"{SERVER_URL}/checkout-sessions/{checkout_id}", headers=get_ucp_headers())
        checkout_resp.raise_for_status()
        current_checkout = checkout_resp.json()
    except Exception as e:
        return f"Error fetching current checkout: {e}"

    line_items = current_checkout.get("line_items", [])
    line_item_ids = [li.get("id") for li in line_items]
    formatted_line_items = []
    for li in line_items:
        formatted_line_items.append({
            "id": li.get("id"),
            "quantity": li.get("quantity"),
            "item": {"id": li.get("item", {}).get("id")}
        })

    payload_trigger = {
        "id": checkout_id,
        "line_items": formatted_line_items,
        "currency": current_checkout.get("currency", "USD"),
        "payment": current_checkout.get("payment", {}),
        "fulfillment": {
            "methods": [
                {
                    "id": "method_1",
                    "type": "shipping",
                    "line_item_ids": line_item_ids
                }
            ]
        }
    }
    try:
        resp = httpx.put(f"{SERVER_URL}/checkout-sessions/{checkout_id}", json=payload_trigger, headers=get_ucp_headers())
        resp.raise_for_status()
        checkout_data = resp.json()
    except Exception as e:
        return f"Error triggering fulfillment options: {e}"

    methods = checkout_data.get("fulfillment", {}).get("methods", [])
    if not methods:
        return "Error: No fulfillment methods available on server."

    method = methods[0]
    destinations = method.get("destinations", [])
    if not destinations:
        return "Fulfillment triggered, but no destinations returned by server."

    dest_id = destinations[0]["id"]
    tool_context.state["fulfillment_method_id"] = method["id"]
    tool_context.state["destination_id"] = dest_id
    tool_context.state["line_item_ids"] = line_item_ids

    payload_select = {
        "id": checkout_id,
        "line_items": formatted_line_items,
        "currency": checkout_data.get("currency", "USD"),
        "payment": checkout_data.get("payment", {}),
        "fulfillment": {
            "methods": [
                {
                    "id": method["id"],
                    "type": "shipping",
                    "line_item_ids": line_item_ids,
                    "selected_destination_id": dest_id
                }
            ]
        }
    }
    try:
        response = httpx.put(f"{SERVER_URL}/checkout-sessions/{checkout_id}", json=payload_select, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        updated_method = data.get("fulfillment", {}).get("methods", [{}])[0]
        groups = updated_method.get("groups", [])
        shipping_options = groups[0].get("options", []) if groups else []
        
        res = f"Fulfillment destination set on server to: {street_address} (Zip: {postal_code})\nAvailable Options:\n"
        for opt in shipping_options:
            amount_usd = opt.get("amount", 0) / 100.0
            opt_id = opt.get("id", "unknown_opt")
            opt_name = opt.get("name", opt.get("title", opt.get("description", "Standard Shipping")))
            res += f"- ID: {opt_id} (Name: {opt_name} - ${amount_usd:.2f})\n"
        return res
    except Exception as e:
        return f"Error setting destination: {e}"

def select_fulfillment_option(tool_context: ToolContext, option_id: str) -> str:
    """Select the preferred shipping option on the server.

    Args:
        tool_context: The tool context containing session state.
        option_id: The ID of the preferred shipping option (e.g. opt_standard).
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session."
    
    fulfillment_method_id = tool_context.state.get("fulfillment_method_id", "method_1")
    destination_id = tool_context.state.get("destination_id")
    line_item_ids = tool_context.state.get("line_item_ids", [])

    if not destination_id:
        return "Error: Please set fulfillment destination first."

    try:
        checkout_resp = httpx.get(f"{SERVER_URL}/checkout-sessions/{checkout_id}", headers=get_ucp_headers())
        checkout_resp.raise_for_status()
        current_checkout = checkout_resp.json()
    except Exception as e:
        return f"Error fetching current checkout: {e}"

    line_items = current_checkout.get("line_items", [])
    formatted_line_items = []
    for li in line_items:
        formatted_line_items.append({
            "id": li.get("id"),
            "quantity": li.get("quantity"),
            "item": {"id": li.get("item", {}).get("id")}
        })

    payload = {
        "id": checkout_id,
        "line_items": formatted_line_items,
        "currency": current_checkout.get("currency", "USD"),
        "payment": current_checkout.get("payment", {}),
        "fulfillment": {
            "methods": [
                {
                    "id": fulfillment_method_id,
                    "type": "shipping",
                    "line_item_ids": line_item_ids,
                    "selected_destination_id": destination_id,
                    "groups": [
                        {
                            "id": "group_1",
                            "line_item_ids": line_item_ids,
                            "selected_option_id": option_id
                        }
                    ]
                }
            ]
        }
    }
    try:
        response = httpx.put(f"{SERVER_URL}/checkout-sessions/{checkout_id}", json=payload, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        totals = data.get("totals", [])
        total = totals[-1].get("amount", 0) / 100.0 if totals else 0.0
        
        shipping_fee = 0.0
        shipping_methods = data.get("fulfillment", {}).get("methods", [])
        if shipping_methods:
            groups = shipping_methods[0].get("groups", [])
            if groups:
                opts = groups[0].get("options", [])
                for o in opts:
                    if o.get("id") == option_id:
                        shipping_fee = o.get("amount", 0) / 100.0
                        break
                        
        tool_context.state["shipping_fee"] = shipping_fee
        return f"Fulfillment option '{option_id}' selected (${shipping_fee:.2f}).\n- Grand Total on server: ${total:.2f}"
    except Exception as e:
        return f"Error selecting shipping option: {e}"

def complete_payment(tool_context: ToolContext, handler_id: str = "mock_payment_handler") -> str:
    """Process the payment on the server using mock_payment_handler and finalize the order.

    Args:
        tool_context: The tool context containing session state.
        handler_id: The ID of the payment handler to use. Defaults to "mock_payment_handler".
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session."
    if "shipping_fee" not in tool_context.state:
        return "Error: Please select shipping options before completing payment."

    payload = {
        "payment": {
            "instruments": [
                {
                    "id": "instr_my_card",
                    "handler_id": handler_id,
                    "type": "card",
                    "display": {
                        "brand": "Visa",
                        "last_digits": "4242"
                    },
                    "credential": {
                        "type": "token",
                        "token": "success_token"
                    },
                    "billing_address": {
                        "street_address": "123 Main St",
                        "address_locality": "Anytown",
                        "address_region": "CA",
                        "address_country": "US",
                        "postal_code": "12345"
                    }
                }
            ]
        },
        "risk_signals": {
            "ip": "127.0.0.1",
            "browser": "python-httpx"
        }
    }
    try:
        response = httpx.post(f"{SERVER_URL}/checkout-sessions/{checkout_id}/complete", json=payload, headers=get_ucp_headers())
        response.raise_for_status()
        data = response.json()
        
        order_id = data.get("id", "UNKNOWN")
        totals = data.get("totals", [])
        amount_paid = totals[-1].get("amount", 0) / 100.0 if totals else 0.0
        
        res = f"🎉 Order finalized successfully on UCP Server via {handler_id}!\n"
        res += f"- Order ID: {order_id}\n"
        res += f"- Total Paid: ${amount_paid:.2f}\n"
        res += f"Thank you for your purchase!"
        
        tool_context.state["checkout_id"] = None
        tool_context.state["shipping_fee"] = None
        tool_context.state["fulfillment_method_id"] = None
        tool_context.state["destination_id"] = None
        tool_context.state["line_item_ids"] = None
        return res
    except Exception as e:
        return f"Error completing payment on server: {e}"



root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful shopping assistant for the UCP Flower Shop. "
        "Your goal is to guide the user through their shopping journey by coordinating the checkout process via the UCP REST Server:\n"
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
