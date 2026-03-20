from flask import Flask, render_template, request, redirect, url_for
import sys
import io

from typing import List, Dict, Any

from contextlib import redirect_stdout

import requests

# Type aliases for readability
Mod = Dict[str, Any]
Order = Dict[str, Any]
Item = Dict[str, Any]

# Global data stores
mods_data: List[Mod] = []
market_data: List[Item] = []

MODS_URL = 'https://raw.githubusercontent.com/WFCD/warframe-items/master/data/json/Mods.json'
MARKET_ITEMS_URL = 'https://api.warframe.market/v2/items'
MARKET_ORDER_URL = 'https://api.warframe.market/v2/items/{}/orders'

# Import the functions from app.py
# from app import getMods, getMarket, loc, mods_data, market_data, find_market_url, fetch_orders_for_mod

app = Flask(__name__)

# Global variables to store search results
search_results = {}


def fetch_json(url: str) -> Any:
    """Helper to fetch and return JSON from a URL."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    print(
        f"❌ Failed to fetch data from {url} — Status code: {response.status_code}"
    )
    return None


def getMods():
    global mods_data
    data = fetch_json(MODS_URL)
    if data:
        mods_data = data
        print(f"✅ Fetched {len(mods_data)} mods.")
    return mods_data


def getMarket():
    global market_data
    data = fetch_json(MARKET_ITEMS_URL)
    if data:
        market_data = data.get("payload", {}).get("items", [])
        print(f"✅ Fetched {len(market_data)} market items.")


def find_market_url(mod_name: str) -> str:
    """Finds the market URL slug for a given mod name."""
    for item in market_data:
        if item.get("item_name", "").lower() == mod_name.lower():
            return item.get("url_name", "")
    return ""


def fetch_orders_for_mod(mod_name: str, mod_url: str) -> List[Order]:
    """Fetch orders for a given mod and tag each order with its mod name and URL."""
    orders_data = fetch_json(MARKET_ORDER_URL.format(mod_url))
    if orders_data:
        orders = orders_data.get("payload", {}).get("orders", [])
        for order in orders:
            order["mod_name"] = mod_name
            order["mod_url"] = mod_url
        return orders
    print(f"⚠️  Failed to fetch orders for '{mod_name}'.")
    return []


def displayOrders(all_orders: List[Dict[str, Any]]):
    print("\nAll Orders (sorted by price: high → low, in-game users only):")

    # Filter only visible, in-game, sell orders
    sell_orders = [
        order for order in all_orders
        if (order.get("visible") and order.get("order_type") == "buy"
            and order.get("user", {}).get("status") == "ingame")
    ]

    # Sort descending by platinum
    sorted_orders = sorted(sell_orders,
                           key=lambda x: x.get("platinum", 0),
                           reverse=True)

    if not sorted_orders:
        print("  No in-game sellers found.")
        return

    for order in sorted_orders:
        user = order.get("user", {})
        ingame_name = user.get("ingame_name", "Unknown")
        mod_name = order.get("mod_name", "Unknown Mod")
        mod_url = order.get("mod_url", "")
        mod_rank = order.get("mod_rank", "N/A")
        platinum = order.get("platinum", "N/A")
        locations = order.get("mod_locations", [])
        locations_str = ", ".join(
            locations) if locations else "Unknown Location"

        print(
            f"  • {ingame_name} [Rank {mod_rank}] → {platinum} platinum → {mod_name} | Locations: {locations_str} | https://warframe.market/items/{mod_url}"
        )


def modified_loc(user_locations: str) -> Dict[str, Any]:
    """Modified version of loc() that returns results instead of printing them"""
    
    getMods()
    getMarket()
    
    locations_map = {
        "1": "Arbiters of Hexis",
        "2": "Cephalon Suda",
        "3": "Steel Meridian",
        "4": "Entrati"
    }

    # Process user input
    user_input = user_locations.split(",")

    # Process input: convert numbers via map, keep others as custom locations
    selected_locations = []
    for val in user_input:
        val = val.strip()
        if val in locations_map:
            print(locations_map[val], file=sys.stderr)
            selected_locations.append(locations_map[val].strip().lower())
        else:
            print(val, file=sys.stderr)
            selected_locations.append(val.strip().lower())

    if not selected_locations:
        return {
            "error": "Invalid input. Please enter at least one valid location."
        }

    matching_mods = set()
    mod_locations = {}

    for mod in mods_data:
        for drop in mod.get("drops", []):
            location = drop.get("location", "").lower()
            if any(search in location for search in selected_locations):
                mod_name = mod.get("name", "Unknown Mod")
                matching_mods.add(mod_name)
                mod_locations.setdefault(mod_name, set()).add(
                    drop.get("location", "Unknown Location"))
                break

    if not matching_mods:
        return {"error": "No mods found for the selected location(s)."}

    # Convert sets to lists for JSON serialization
    for mod_name in mod_locations:
        mod_locations[mod_name] = list(mod_locations[mod_name])

    # Fetch market orders
    all_orders: List[Dict[str, Any]] = []
    for mod_name in matching_mods:
        mod_url = find_market_url(mod_name)
        if not mod_url:
            continue
        orders = fetch_orders_for_mod(mod_name, mod_url)
        for order in orders:
            order["mod_locations"] = mod_locations.get(mod_name, [])
        all_orders.extend(orders)

    # Filter and sort orders (only visible, in-game, buy orders)
    sell_orders = [
        order for order in all_orders
        if (order.get("visible") and order.get("order_type") == "buy"
            and order.get("user", {}).get("status") == "ingame")
    ]

    # Sort descending by platinum
    sorted_orders = sorted(sell_orders,
                           key=lambda x: x.get("platinum", 0),
                           reverse=True)

    return {
        "mods_found": mod_locations,
        "orders": sorted_orders,
        "search_query": user_locations
    }


@app.route('/')
def index():
    """Show the main search form"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Handle form submission and show results"""
    locations = request.form.get('locations', '')
    if not locations:
        return render_template('results.html',
                               error="Please enter at least one location",
                               search_query="")

    # Call the modified loc function
    results = modified_loc(locations)
    return render_template('results.html',
                           mods_found=results.get('mods_found', {}),
                           orders=results.get('orders', []),
                           error=results.get('error'),
                           search_query=results.get('search_query', locations))


if __name__ == '__main__':
    # Initialize data on startup

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
