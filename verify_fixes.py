import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_file_content(filepath, search_strings):
    """Check if a file contains specific strings"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing = []
        for s in search_strings:
            if s not in content:
                missing.append(s)
        
        if missing:
            print(f"❌ {os.path.basename(filepath)}: Missing expected content:")
            for m in missing:
                print(f"   - {m[:50]}...")
            return False
        else:
            print(f"✅ {os.path.basename(filepath)}: Verified")
            return True
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return False

def verify_code_changes():
    print("--- Verifying Code Changes ---")
    
    # 1. Check graph_utils.py for clear_database
    check_file_content('graph_utils.py', ['def clear_database():', 'MATCH (n) DETACH DELETE n'])
    
    # 2. Check app.py for clear_database call
    check_file_content('app.py', ['from graph_utils import', 'clear_database', "if 'db_cleared' not in st.session_state:"])
    
    # 3. Check extract_graph.py for CHUNK_SIZE and prompt
    check_file_content('extract_graph.py', ['CHUNK_SIZE = 20000', 'EXHAUSTIVELY extract', 'aim for 20-50+ per chunk'])
    
    # 4. Check agents.py for restricted prompts
    check_file_content('agents.py', [
        'strictly rely on the provided knowledge graph',
        'ONLY in the graph',
        'CITE the specific graph connections'
    ])

def verify_database_connection():
    print("\n--- Verifying Database Connection & Clearing ---")
    try:
        from graph_utils import get_neo4j_driver, clear_database, get_graph_stats
        
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Create a test node
            session.run("CREATE (n:TestNode {name: 'VerificationTest'})")
            print("✅ Created test node")
            
            # Check stats
            stats = get_graph_stats()
            print(f"   Nodes before clear: {stats['nodes']}")
            
            # Clear database
            print("   Running clear_database()...")
            success = clear_database()
            
            if success:
                print("✅ clear_database() returned True")
                # Check stats again
                stats_after = get_graph_stats()
                print(f"   Nodes after clear: {stats_after['nodes']}")
                
                if stats_after['nodes'] == 0:
                    print("✅ Database is empty")
                else:
                    print("❌ Database is NOT empty")
            else:
                print("❌ clear_database() returned False")
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        print("   (This might be expected if Neo4j is not running locally)")

if __name__ == "__main__":
    verify_code_changes()
    verify_database_connection()
