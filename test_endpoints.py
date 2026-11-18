from app.main import app
from starlette.testclient import TestClient

client = TestClient(app)
org = 'c1a2b3d4-e5f6-7890-abcd-ef1234567890'

print("=== 1. GET /orgs/{org_id}/domains ===")
r = client.get(f'/orgs/{org}/domains')
print('Status:', r.status_code, '| Items:', len(r.json()['items']))
print('First domain:', r.json()['items'][0])

print("\n=== 2. POST /orgs/{org_id}/domains/check ===")
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'milesweb.com'})
print('Check existing (milesweb.com):', r.status_code, r.json())
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'newavailabledomainxyz.com'})
print('Check available:', r.status_code, r.json())

print("\n=== 2c. POST /orgs/{org_id}/domains/check/suggestions ===")
r = client.post(f'/orgs/{org}/domains/check/suggestions', json={'domain': 'dfdf'})
print('Check suggestions for dfdf:', r.status_code, '| Count:', len(r.json()['suggestions']))
for s in r.json()['suggestions']:
    print(f"  {s['domain']}: available={s['available']}, free_1st_yr={s['free_first_year']}, pricing={s['pricing']}")

print("\n=== 3. GET /orgs/{org_id}/plans ===")
r = client.get(f'/orgs/{org}/plans')
print('Status:', r.status_code, '| Plans count:', len(r.json()['items']))
for p in r.json()['items']:
    print(f"  ID: {p['id']} - {p['name']} ({p['planType']})")

print("\n=== 4. GET /orgs/{org_id}/plans/{plan_id} ===")
r = client.get(f'/orgs/{org}/plans/1003')
p = r.json()
print(f"Plan 1003: {p['name']} | cgroupLimits memoryLimit: {p['cgroupLimits']['memoryLimit']} | fsQuota: {p['fsQuotaLimit']['totalAvailable']}")

print("\n=== 5. GET /orgs/{org_id}/plans/pricing (INR 36m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=inr&billingCycle=triennially')
print('Status:', r.status_code)
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ₹{item['price_per_month']['discounted']}/mo (Orig: ₹{item['price_per_month']['original']}, Renews: ₹{item['price_per_month']['renewal']}) | Total: ₹{item['total_price']} + GST: ₹{item['tax']['amount']} = ₹{item['grand_total']}")

print("\n=== 5b. GET /orgs/{org_id}/plans/pricing (USD 36m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=usd&billingCycle=triennially')
print('Status:', r.status_code)
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ${item['price_per_month']['discounted']}/mo (Orig: ${item['price_per_month']['original']}) | Total: ${item['total_price']}")

print("\n=== 5c. GET /orgs/{org_id}/plans/pricing (INR 12m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=inr&billingCycle=annually')
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ₹{item['price_per_month']['discounted']}/mo | Total 12m: ₹{item['total_price']} + GST 18%: ₹{item['tax']['amount']} = ₹{item['grand_total']}")

print("\n=== 6. GET /orgs/{org_id}/plans/compare ===")
r = client.get(f'/orgs/{org}/plans/compare')
print('Status:', r.status_code, '| Categories:', [c['name'] for c in r.json()['categories']])
