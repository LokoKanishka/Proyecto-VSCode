import os
import yaml
import sys

def load_config(path="config.yaml"):
    """
    Loads config from yaml, applies defaults, and validates critical fields.
    Returns dict or raises Exception/prints warnings.
    """
    if not os.path.exists(path):
        print(f"WARN: Config file {path} not found. Using defaults.")
        return {}

    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"ERROR: Failed to parse {path}: {e}")
        return {}

    errors = []
    
    # Validation logic
    # Sample Rate (top level)
    sr = config.get("sample_rate")
    if sr and sr not in [16000, 44100, 48000]:
        errors.append(f"Invalid sample_rate: {sr}. Must be 16000, 44100, or 48000.")

    # Timeouts (web_search.timeout_s)
    to = config.get("web_search", {}).get("timeout_s")
    if to and (not isinstance(to, (int, float)) or to <= 0):
        errors.append(f"Invalid web_search.timeout_s: {to}. Must be > 0.")

    # URLs (web_search.searxng_url)
    searx = config.get("web_search", {}).get("searxng_url")
    if searx and not searx.startswith("http"):
        errors.append(f"Invalid web_search.searxng_url: {searx}. Must start with http.")

    if errors:
        for err in errors:
            print(f"CONFIG ERROR: {err}", file=sys.stderr)
        raise ValueError(f"Configuration validation failed with {len(errors)} errors.")

    return config

if __name__ == "__main__":
    # Doctor mode
    try:
        cfg = load_config()
        print("Config OK.")
        # Print summary
        print(f"Loaded {len(cfg)} top-level keys.")
    except Exception as e:
        print(f"Doctor Status: FAILED ({e})", file=sys.stderr)
        sys.exit(2)
