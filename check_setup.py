"""
Setup verification script to check if all dependencies and configurations are correct.
"""
import os
import sys
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("🔍 Checking .env file...")
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("   Please create a .env file based on .env.example")
        return False
    
    load_dotenv()
    required_vars = ['GOOGLE_API_KEY', 'NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    print("✅ .env file configured correctly")
    return True

def check_neo4j_connection():
    """Check Neo4j connection"""
    print("\n🔍 Checking Neo4j connection...")
    try:
        from neo4j import GraphDatabase
        load_dotenv()
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        driver.close()
        
        print("✅ Neo4j connection successful")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        print("   Please ensure Neo4j is running and credentials are correct")
        return False

def check_python_packages():
    """Check if required Python packages are installed"""
    print("\n🔍 Checking Python packages...")
    required_packages = [
        'streamlit',
        'langchain',
        'langchain_community',
        'langchain_google_genai',
        'crewai',
        'neo4j',
        'pdfplumber',
        'pyvis',
        'networkx',
        'pydantic'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Please run: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages installed")
    return True

def check_gemini_api():
    """Check Gemini API key"""
    print("\n🔍 Checking Gemini API key...")
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ Gemini API key not configured")
        print("   Please set GOOGLE_API_KEY in your .env file")
        return False
    
    # Try to import and create a simple client
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            max_retries=1,
            request_timeout=10
        )
        # Simple test - just check if it can be created
        print("✅ Gemini API key configured")
        return True
    except Exception as e:
        print(f"⚠️  Gemini API key may be invalid: {e}")
        return False

def main():
    """Run all checks"""
    print("=" * 50)
    print("🧬 AI Research Knowledge Graph - Setup Check")
    print("=" * 50)
    
    results = []
    results.append(("Environment File", check_env_file()))
    results.append(("Python Packages", check_python_packages()))
    results.append(("Gemini API", check_gemini_api()))
    results.append(("Neo4j Connection", check_neo4j_connection()))
    
    print("\n" + "=" * 50)
    print("📊 Summary")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 All checks passed! You're ready to run the application.")
        print("   Run: streamlit run app.py")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())






