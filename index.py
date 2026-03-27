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

if __name__ == '__main__':
    # Initialize data on startup

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
