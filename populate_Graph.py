import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase



URI = "bolt://localhost:7687" 
AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

# 1. Load Secrets
load_dotenv()
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

# 2. Define the Query
# This Cypher query checks if nodes exist, if not creates them, then creates the relationship
IMPORT_QUERY = """
UNWIND $triples AS row
MERGE (h:Entity {name: row.head, session_id: $session_id})
MERGE (t:Entity {name: row.tail, session_id: $session_id})
MERGE (h)-[r:RELATION {type: row.relation}]->(t)
SET r.session_id = $session_id
"""

def populate_neo4j(json_file_path, session_id=None):
    """
    Populate Neo4j database with triples from JSON file.
    
    Args:
        json_file_path: Path to JSON file containing triples
        session_id: Unique session ID to tag nodes with
    
    Returns:
        tuple: (success: bool, message: str, count: int)
    """
    # Check if file exists first
    if not os.path.exists(json_file_path):
        error_msg = f"❌ Error: The file '{json_file_path}' was not found!"
        print(error_msg)
        return False, error_msg, 0

    # Connect to Neo4j
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
        print("✅ Connected to Neo4j...")
        
        # Load your JSON data
        with open(json_file_path, 'r') as f:
            data = json.load(f)
            
        if not data:
            warning_msg = "⚠️ Warning: The JSON file is empty."
            print(warning_msg)
            driver.close()
            return False, warning_msg, 0
            
        if not session_id:
            print("⚠️ Warning: No session_id provided. Nodes will be created without session isolation.")

        print(f"🚀 Importing {len(data)} triples into Neo4j for session {session_id}...")
        with driver.session() as session:
            session.run(IMPORT_QUERY, triples=data, session_id=session_id)
            success_msg = f"✅ Success! Imported {len(data)} triples."
            print(success_msg)
        
        driver.close()
        return True, success_msg, len(data)
    except Exception as e:
        error_msg = f"❌ Database Error: {e}"
        print(error_msg)
        return False, error_msg, 0

if __name__ == "__main__":
    # Make sure this matches the output file from extract_graph.py
    populate_neo4j("triples.json")