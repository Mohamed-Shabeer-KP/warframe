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
MARKET_ORDER_URL = 'https://api.warframe.market/v2/orders/item/{}'

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

def getMarket():
    global market_data
    data = fetch_json(MARKET_ITEMS_URL)
    if data:
        market_data = data.get("data", [])
        print(f"✅ Fetched {len(market_data)} market items.")

def getMods(mod_location: str):
    global mods_data
    if market_data:
        # Check for gameRef in market_data items and filter by mod_location 
        mods_data = [item for item in market_data if mod_location.lower() in item.get("tags", "")]
        print(f"✅ Fetched {len(mods_data)} mods.")
    return mods_data

def fetch_orders_for_mod(mod_slug: str) -> List[Order]:
    """Fetch orders for a given mod and tag each order with its mod name and URL."""
    orders_data = fetch_json(MARKET_ORDER_URL.format(mod_slug))
    print(f"🔍 Fetching orders for '{mod_slug}' from URL: {MARKET_ORDER_URL.format(mod_slug)}")
    return orders_data
    print(f"⚠️  Failed to fetch orders for '{mod_slug}'.")
    return []

def modified_loc(user_locations: str) -> Dict[str, Any]:
    """Modified version of loc() that returns results instead of printing them"""
    
    print(f"🔍 Fetching market")
    getMarket()
    
    locations_map = {
        "1": "augment",
        "2": "warframe",
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

    print(f"🔍 Fetching mods")
    mods_list = []
    for loc in selected_locations:
        mods_list.append(getMods(loc))

    # Fetch market orders
    all_orders = []
    for mod in mods_data:
        orders = fetch_orders_for_mod(mod['slug'])

        for x in orders['data']:
            x['mod_name'] = mod['slug']

        all_orders.append(orders['data'])

    # Filter and sort orders (only visible, in-game, buy orders)
    sell_orders = []
    for orders in all_orders:
        for order in orders:
            if (order['visible'] and order['type'] == 'buy' and order['user']['status'] == 'ingame'):
                sell_orders.append(order)

    # Sort descending by platinum
    sorted_orders = sorted(sell_orders,
                           key=lambda x: x.get("platinum", 0),
                           reverse=True)

    return {
        "orders": sorted_orders
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
