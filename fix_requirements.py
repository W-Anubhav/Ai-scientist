"""
Script to fix LangChain version compatibility issues
"""
import subprocess
import sys

def fix_versions():
    """Uninstall and reinstall compatible versions"""
    print("🔧 Fixing LangChain version compatibility issues...")
    print("=" * 60)
    
    packages_to_reinstall = [
        "langchain==0.3.27",
        "langchain-core==0.3.27",
        "langchain-community==0.3.27",
        "langchain-google-genai==2.0.0",
    ]
    
    print("\n1️⃣ Uninstalling conflicting packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", 
                             "langchain", "langchain-core", "langchain-community", 
                             "langchain-google-genai"])
        print("✅ Uninstalled successfully")
    except Exception as e:
        print(f"⚠️  Some packages may not have been uninstalled: {e}")
    
    print("\n2️⃣ Installing compatible versions...")
    for package in packages_to_reinstall:
        try:
            print(f"   Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"   ✅ {package} installed")
        except Exception as e:
            print(f"   ❌ Failed to install {package}: {e}")
    
    print("\n3️⃣ Verifying installation...")
    try:
        from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
        print("✅ GraphCypherQAChain import successful!")
        return True
    except Exception as e:
        print(f"❌ Import still failing: {e}")
        print("\n💡 Try running: pip install --upgrade langchain langchain-core langchain-community langchain-google-genai")
        return False

if __name__ == "__main__":
    success = fix_versions()
    if success:
        print("\n🎉 Version fix complete! You can now run the application.")
    else:
        print("\n⚠️  Please check the error messages above and try manual installation.")
    sys.exit(0 if success else 1)






