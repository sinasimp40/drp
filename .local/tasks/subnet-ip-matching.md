# Subnet-Based IP Matching

## What & Why
In a diskless setup, the server and client PCs often have different public IPs from the same subnet (e.g., server=103.188.86.230, PC1=103.188.86.231, PC2=103.188.86.232). The current exact IP match causes false suspensions. Changing to subnet matching (first 3 octets) allows all devices on the same network while still blocking connections from completely different networks.

## Done looks like
- License activation still records the full registered_ip
- Heartbeat and validate endpoints compare only the first 3 octets of the IP (e.g., 103.188.86.x matches 103.188.86.y)
- Licenses are no longer suspended when the IP changes within the same subnet
- Connections from a different subnet (e.g., 45.77.100.x vs 103.188.86.x) still trigger suspension
- Dashboard still shows the full IP addresses for reference
- A helper function centralizes the subnet comparison logic so both check points use the same logic
- End-to-end tested: same-subnet IPs pass, different-subnet IPs still get caught

## Out of scope
- HWID binding or machine name binding (separate feature if needed later)
- IPv6 support (current system is IPv4 only)
- Admin-configurable subnet mask size

## Tasks
1. **Add a subnet comparison helper** — Create a helper function `_is_same_subnet(ip1, ip2)` that compares the first 3 octets of two IPv4 addresses. Returns True if they match (e.g., 103.188.86.230 vs 103.188.86.231).

2. **Update heartbeat IP check** — Replace the exact IP comparison in the heartbeat endpoint with the subnet comparison helper.

3. **Update validate IP check** — Replace the exact IP comparison in the validate endpoint with the subnet comparison helper.

4. **Test the change** — Verify same-subnet IPs are accepted and different-subnet IPs are still blocked, using direct API calls with signed requests.

## Relevant files
- `license_server/server.py:335-341`
- `license_server/server.py:427-433`
- `license_server/server.py:251-258`
