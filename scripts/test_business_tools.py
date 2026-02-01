from src.skills.business_tools import BusinessTools
import os

def test_tools():
    print("🧪 Testing Business Tools...")
    tools = BusinessTools()
    
    # 1. Shipping
    print("📦 Testing Shipping Calculator...")
    res = tools.calculate_shipping("Madrid", 10.0)
    print(f"   Result: {res}")
    assert res['cost_usd'] > 0
    assert "Madrid" in res['destination']
    
    # 2. PDF Gen
    print("📄 Testing PDF Generator...")
    items = [{"name": "Camera", "qty": 2, "price": 100}, {"name": "Monitor", "qty": 1, "price": 200}]
    path = tools.generate_quote_pdf(items, "Cliente Test")
    print(f"   PDF Created at: {path}")
    assert os.path.exists(path)
    
    print("✅ All Business Tools Verified.")

if __name__ == "__main__":
    test_tools()
