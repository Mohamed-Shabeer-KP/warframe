from flask import Flask, render_template, request, redirect, url_for
import sys
import io

from typing import List, Dict, Any

from contextlib import redirect_stdout

import requests

app = Flask(__name__)
app.secret_key = "your_secret_key_here" 

# Type aliases for readability
Mod = Dict[str, Any]
Order = Dict[str, Any]
Item = Dict[str, Any]

# Global data stores
mods_data: List[Mod] = []
market_data: List[Item] = []

MARKET_ITEMS_URL = 'https://api.warframe.market/v2/items'
MARKET_ORDER_URL = 'https://api.warframe.market/v2/orders/item/{}'
PATEBIN_URL_COLLECTION = 'https://pastebin.com/raw/DugQBXdL'

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

def getMod(mod_location: str):
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

def getMainPaste():
    """Fetch main warframe collection paste"""
    try:
        response = requests.get(PATEBIN_URL_COLLECTION)
        if response.status_code == 200:
            pastebin_url_list = response.text.strip().splitlines()
            return {
                "paste": pastebin_url_list
            }
        print(f"❌ Failed to fetch data from Pastebin — Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching data from Pastebin: {e}")
    return []

def processMainPaste():
    """Fetch main warframe collection paste"""
    try:
        response = requests.get(PATEBIN_URL_COLLECTION)
        if response.status_code == 200:
            pastebin_url_list = response.text.strip().splitlines()
            # for line in pastebin_url_list:
            #     if line:
            #         parts = line.split("|")
            #         if len(parts) >= 2:  # make sure we have at least key and value
            #             key = parts[0]
            #             value = parts[1]
            #             mapping[key] = value
            return pastebin_url_list
        print(f"❌ Failed to fetch data from Pastebin — Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching data from Pastebin: {e}")
    return []

def getPaste(pastebin_url: str):
    """Fetch mod list from Pastebin URL and return as a list of mod slugs."""
    try:
        response = requests.get(pastebin_url)
        if response.status_code == 200:
            mods_list = response.text.strip().splitlines()
            print(f"✅ Fetched {len(mods_list)} mods from Pastebin.")
            return mods_list
        print(f"❌ Failed to fetch data from Pastebin — Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching data from Pastebin: {e}")
    return []

def processInput(user_input: str):
    """Process user input"""

    if user_input.isdigit():
        pastebin_dict = processMainPaste()
        # if user_input in pastebin_dict:
        #     pastebin_mods = getPaste(pastebin_dict[user_input])
        # else:
        #     print("Not found")
    else:
        pastebin_mods = getPaste(user_input)

    print(f"🔍 Fetching orders")
    all_orders = []
    error_list = []
    for mod in pastebin_mods:
        try:
            orders = fetch_orders_for_mod(mod)

            for x in orders['data']:
                x['mod_name'] = mod

            all_orders.append(orders['data'])
        except Exception as e:
            print(f"❌ Error fetching orders for mod '{mod}': {e}")
            error = f"Error fetching orders for mod '{mod}': {e}"
            error_list.append(error)

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
        "orders": sorted_orders,
        "error":  error_list
    }


@app.route('/')
def index():
    """Show the main search form"""
    results = getMainPaste()
    return render_template('index.html',
                            paste=results.get('paste', []))

@app.route('/search', methods=['POST'])
def search():
    """Handle form submission and show results"""
    user_input = request.form.get('user_input', '')
    if not user_input:
        return render_template('results.html',
                               error="Please enter an input",
                               search_query="")

    # Call the modified loc function
    results = processInput(user_input)
    return render_template('results.html',
                           mods_found=results.get('mods_found', {}),
                           orders=results.get('orders', []),
                           error=results.get('error'),
                           search_query=results.get('search_query', user_input))

if __name__ == '__main__':
    # Initialize data on startup

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
