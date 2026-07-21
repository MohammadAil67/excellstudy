import sys
import os
import json
import urllib.request
import urllib.error


def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_manifest.py <path_to_manifest.json> <agent_slug>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    agent_slug = sys.argv[2]

    # 1. Load manifest.json
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse manifest JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Call Django API check-registration
    host = os.environ.get('EXCELLSTUDY_HOST', 'http://localhost:8000')
    url = f"{host.rstrip('/')}/developer/api/agents/check-registration/?slug={agent_slug}"

    print(f"Querying platform registration for slug: {agent_slug} at {url}...")
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as response:
            registration = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Rejection: No pending agent registration found on the portal for slug '{agent_slug}'.", file=sys.stderr)
            print("Please register your agent in the developer portal before pushing your image.", file=sys.stderr)
        else:
            print(f"Error: Server returned HTTP {e.code} during lookup: {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to connect to platform API: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Cross-validate input_type
    manifest_input = manifest.get('input_type')
    registered_input = registration.get('input_type')
    if manifest_input != registered_input:
        print("Rejection: Input type mismatch!", file=sys.stderr)
        print(f"  Registered in Portal: '{registered_input}'", file=sys.stderr)
        print(f"  Declared in Manifest: '{manifest_input}'", file=sys.stderr)
        sys.exit(1)

    # 4. Cross-validate output_types
    manifest_outputs = manifest.get('output_types', [])
    registered_outputs = registration.get('output_types', [])
    if not isinstance(manifest_outputs, list):
        print(f"Error: 'output_types' in manifest.json must be a list, got {type(manifest_outputs).__name__}", file=sys.stderr)
        sys.exit(1)

    if set(manifest_outputs) != set(registered_outputs):
        print("Rejection: Output types mismatch!", file=sys.stderr)
        print(f"  Registered in Portal: {set(registered_outputs)}", file=sys.stderr)
        print(f"  Declared in Manifest: {set(manifest_outputs)}", file=sys.stderr)
        sys.exit(1)

    # 5. Validate required endpoints are present
    required_endpoints = ['invoke', 'health', 'capabilities']
    endpoints_section = manifest.get('endpoints', {})
    missing_endpoints = [
        ep for ep in required_endpoints 
        if ep not in manifest and ep not in endpoints_section
    ]
    if missing_endpoints:
        print(f"Rejection: Missing required endpoint declarations in manifest: {missing_endpoints}", file=sys.stderr)
        sys.exit(1)

    print("Success: Manifest cross-validation passed successfully!")
    sys.exit(0)


if __name__ == '__main__':
    main()
