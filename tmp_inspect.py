import requests

url='https://api.warframe.market/v2/items'
resp=requests.get(url)
print('status', resp.status_code)
data=resp.json().get('data', [])
print('items', len(data))
for i in range(3):
    item=data[i]
    print(i, item.get('id'), item.get('url_name'), type(item.get('items_in_set')))
    if i==0:
        print('keys', list(item.keys())[:20])

if data:
    slug=data[0].get('url_name')
    oresp=requests.get(f'https://api.warframe.market/v2/orders/{slug}')
    print('orders status', oresp.status_code)
    od=oresp.json().get('payload', {})
    print('payload keys', list(od.keys()))
    orders=od.get('orders', [])
    print('orders len', len(orders))
    if orders:
        print('order keys', list(orders[0].keys()))
        user=orders[0].get('user', {})
        print('user keys', list(user.keys()))
        # check for gameRef in order or user
        print('order gameRef', orders[0].get('gameRef'))
        print('user gameRef', user.get('game_ref') or user.get('ingame_name'))
