"""Unit tests for the name generator."""
from services.name_generator import generate_deploy_name, get_expected_url

def test(label, raw, platform, custom=None, expected_max=None):
    name = generate_deploy_name(raw, platform, custom)
    max_len = {"Netlify": 63, "Cloudflare": 50, "Vercel": 63, "Render": 30}.get(platform, 63)
    ok_len = len(name) <= max_len
    ok_chars = all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name)
    ok_start = name[0] != "-" if name else False
    ok_end = name[-1] != "-" if name else False
    ok_min = len(name) >= 3
    passed = all([ok_len, ok_chars, ok_start, ok_end, ok_min])
    status = "PASS" if passed else "FAIL"
    safe_raw = raw.encode("ascii", errors="replace").decode()
    print(f"  [{status}] {label}: '{safe_raw}' -> '{name}' (len={len(name)}/{max_len})")
    if not passed:
        if not ok_len: print(f"    ! Length {len(name)} > {max_len}")
        if not ok_chars: print(f"    ! Invalid chars in: {name}")
        if not ok_start: print(f"    ! Starts with hyphen")
        if not ok_end: print(f"    ! Ends with hyphen")
        if not ok_min: print(f"    ! Too short (< 3)")
    return passed

print("=" * 60)
print("  Name Generator Tests")
print("=" * 60)

results = []

# Basic conversions
results.append(test("lowercase", "My-Project", "Netlify"))
results.append(test("spaces", "Cafe Noir Indiranagar", "Netlify"))
results.append(test("special chars", "café_noir@v2!", "Cloudflare"))
results.append(test("underscores", "my_project_name", "Vercel"))
results.append(test("dots", "app.server.v3", "Render"))

# Edge cases
results.append(test("empty", "", "Netlify"))
results.append(test("single char", "x", "Netlify"))
results.append(test("hyphens only", "---", "Netlify"))
results.append(test("numbers only", "12345", "Vercel"))
results.append(test("unicode", "日本語プロジェクト", "Netlify"))

# Length limits
results.append(test("long name netlify", "a" * 100, "Netlify"))
results.append(test("long name cloudflare", "b" * 100, "Cloudflare"))
results.append(test("long name render", "c" * 100, "Render"))

# Custom name override
results.append(test("custom name", "original-name", "Netlify", custom="my-custom-cafe"))
results.append(test("custom with spaces", "original", "Cloudflare", custom="My Cafe Site"))

# Real project names
results.append(test("real 1", "Cafe Noir Indiranagar - Website", "Netlify"))
results.append(test("real 2", "portfolio_v2_final (2)", "Cloudflare"))
results.append(test("real 3", "John's React App", "Vercel"))
results.append(test("real 4", "fastapi-backend-service-production-v3.2", "Render"))

print(f"\n{'=' * 60}")
passed = sum(results)
total = len(results)
print(f"  Results: {passed}/{total} passed")
print(f"{'=' * 60}")

# Test URL generation
print("\n  Expected URLs:")
for p in ["Netlify", "Cloudflare", "Vercel", "Render"]:
    name = generate_deploy_name("Cafe Noir Indiranagar", p)
    url = get_expected_url(name, p)
    print(f"    {p}: {url}")
