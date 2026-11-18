from app.main import app
from starlette.testclient import TestClient

client = TestClient(app)
org = 'c1a2b3d4-e5f6-7890-abcd-ef1234567890'

print("=== 1. GET /orgs/{org_id}/domains ===")
r = client.get(f'/orgs/{org}/domains')
print('Status:', r.status_code, '| Items:', len(r.json()['items']))
print('First domain:', r.json()['items'][0])

print("\n=== 2. POST /orgs/{org_id}/domains/check (Enhance pre-flight) ===")
# 2a. Real available domain
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'sweetcrumbs.in'})
print('Check valid available (sweetcrumbs.in):', r.status_code, r.json())

# 2b. Fake / non-existent TLD (.lbcom) -> MUST be prohibited
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'soham.lbcom'})
print('Check fake TLD (soham.lbcom):', r.status_code, r.json())
assert r.json()['status'] == 'prohibited', "Expected prohibited for fake TLD .lbcom"

# 2c. In-use domain in current org
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'milesweb.com'})
print('Check existing org domain (milesweb.com):', r.status_code, r.json())
assert r.json()['status'] == 'in-use-same-org'
assert r.json()['websiteId'] is not None

# 2d. Globally taken domain
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'google.com'})
print('Check globally taken (google.com):', r.status_code, r.json())
assert r.json()['status'] == 'in-use-other-org'

# 2e. Missing TLD (sweetcrumbs) -> 400 Bad Request
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'sweetcrumbs'})
print('Check missing TLD (sweetcrumbs):', r.status_code, r.json())
assert r.status_code == 400

# 2f. Auto-cleaning URL format (https://www.sweetcrumbs.in/)
r = client.post(f'/orgs/{org}/domains/check', json={'domain': 'https://www.sweetcrumbs.in/'})
print('Check URL auto-cleaning (https://www.sweetcrumbs.in/):', r.status_code, r.json())
assert r.json()['status'] == 'available'

print("\n=== 2g. POST /orgs/{org_id}/domains/check/suggestions ===")
r = client.post(f'/orgs/{org}/domains/check/suggestions', json={'domain': 'dfdf'})
print('Suggestions count:', len(r.json()['suggestions']))
for s in r.json()['suggestions']:
    print(f"  {s['domain']}: available={s['available']}, free_1st_yr={s['free_first_year']}, pricing={s['pricing']}")

print("\n=== 3. GET /orgs/{org_id}/plans ===")
r = client.get(f'/orgs/{org}/plans')
print('Status:', r.status_code, '| Plans count:', len(r.json()['items']))

print("\n=== 4. GET /orgs/{org_id}/plans/{plan_id} ===")
r = client.get(f'/orgs/{org}/plans/1003')
p = r.json()
print(f"Plan 1003: {p['name']} | cgroupLimits: {p['cgroupLimits']['memoryLimit']} bytes | fsQuota: {p['fsQuotaLimit']['totalAvailable']} bytes")

print("\n=== 5. GET /orgs/{org_id}/plans/pricing (INR 36m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=inr&billingCycle=triennially')
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ₹{item['price_per_month']['discounted']}/mo | Total: ₹{item['total_price']} + GST: ₹{item['tax']['amount']} = ₹{item['grand_total']}")

print("\n=== 5b. GET /orgs/{org_id}/plans/pricing (USD 36m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=usd&billingCycle=triennially')
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ${item['price_per_month']['discounted']}/mo | Total: ${item['total_price']}")

print("\n=== 5c. GET /orgs/{org_id}/plans/pricing (INR 12m) ===")
r = client.get(f'/orgs/{org}/plans/pricing?currency=inr&billingCycle=annually')
for item in r.json()['plans']:
    print(f"  {item['plan_name']}: ₹{item['price_per_month']['discounted']}/mo | Total: ₹{item['total_price']} + GST: ₹{item['tax']['amount']} = ₹{item['grand_total']}")

print("\n=== 6. GET /orgs/{org_id}/plans/compare ===")
r = client.get(f'/orgs/{org}/plans/compare')
print('Categories:', [c['name'] for c in r.json()['categories']])
print('\nALL TESTS PASSED SUCCESSFULLY!')
