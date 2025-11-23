"""
Fix for langchain_core.memory import error
This script ensures all dependencies are correctly installed
"""
import subprocess
import sys

def fix_memory_error():
    print("🔧 Fixing langchain_core.memory import error...")
    print("=" * 60)
    
    # Check if we're in venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not in virtual environment - installing globally")
    
    # Reinstall langchain packages to ensure compatibility
    packages = [
        "langchain-core==0.3.80",
        "langchain==0.3.27",
        "langchain-community==0.3.27"
    ]
    
    print("\n📦 Reinstalling LangChain packages...")
    for package in packages:
        try:
            print(f"   Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", package])
            print(f"   ✅ {package} installed")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print("\n🧪 Testing imports...")
    try:
        from langchain_core.memory import BaseMemory
        print("✅ langchain_core.memory import successful")
    except Exception as e:
        print(f"❌ Still failing: {e}")
        print("\n💡 Try: pip install --upgrade langchain-core langchain langchain-community")
        return False
    
    try:
        from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
        print("✅ GraphCypherQAChain import successful")
    except Exception as e:
        print(f"❌ GraphCypherQAChain failing: {e}")
        return False
    
    print("\n🎉 All imports working! The error should be fixed.")
    return True

if __name__ == "__main__":
    success = fix_memory_error()
    sys.exit(0 if success else 1)





