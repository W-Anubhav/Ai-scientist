import os
import uuid
from dotenv import load_dotenv
from graph_utils import get_neo4j_driver, clear_database, get_graph_stats

# Load environment variables
load_dotenv()

def verify_session_isolation():
    print("--- Verifying Session Isolation ---")
    
    # Generate two fake session IDs
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())
    
    print(f"Session A: {session_a}")
    print(f"Session B: {session_b}")
    
    driver = get_neo4j_driver()
    
    try:
        with driver.session() as session:
            # 1. Create data for Session A
            print("\n1. Creating data for Session A...")
            session.run("""
                CREATE (n:Entity {name: 'NodeA', session_id: $sid})
                CREATE (m:Entity {name: 'NodeA2', session_id: $sid})
                CREATE (n)-[:RELATION {type: 'TEST', session_id: $sid}]->(m)
            """, sid=session_a)
            
            # 2. Create data for Session B
            print("2. Creating data for Session B...")
            session.run("""
                CREATE (n:Entity {name: 'NodeB', session_id: $sid})
            """, sid=session_b)
            
            # 3. Verify Stats for Session A
            stats_a = get_graph_stats(session_id=session_a)
            print(f"\nStats for Session A: {stats_a['nodes']} nodes (Expected: 2)")
            if stats_a['nodes'] == 2:
                print("✅ Session A sees correct node count")
            else:
                print("❌ Session A sees INCORRECT node count")
                
            # 4. Verify Stats for Session B
            stats_b = get_graph_stats(session_id=session_b)
            print(f"Stats for Session B: {stats_b['nodes']} nodes (Expected: 1)")
            if stats_b['nodes'] == 1:
                print("✅ Session B sees correct node count")
            else:
                print("❌ Session B sees INCORRECT node count")
                
            # 5. Verify Stats for Global (No Session)
            # Note: get_graph_stats without session_id returns global count
            stats_global = get_graph_stats()
            print(f"Global Stats: {stats_global['nodes']} nodes (Expected >= 3)")
            
            # 6. Test Clear Database for Session A
            print("\n6. Clearing Session A...")
            clear_database(session_id=session_a)
            
            stats_a_after = get_graph_stats(session_id=session_a)
            stats_b_after = get_graph_stats(session_id=session_b)
            
            print(f"Stats for Session A after clear: {stats_a_after['nodes']} nodes (Expected: 0)")
            print(f"Stats for Session B after clear: {stats_b_after['nodes']} nodes (Expected: 1)")
            
            if stats_a_after['nodes'] == 0 and stats_b_after['nodes'] == 1:
                print("✅ Isolation Verified: Clearing Session A did not affect Session B")
            else:
                print("❌ Isolation Failed!")
                
            # Cleanup Session B
            clear_database(session_id=session_b)
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    verify_session_isolation()
