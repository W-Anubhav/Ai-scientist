"""
Utility functions for knowledge graph visualization and querying.
"""
import os
from typing import List, Dict, Tuple
from neo4j import GraphDatabase
from dotenv import load_dotenv
import networkx as nx
from pyvis.network import Network

load_dotenv()

def get_neo4j_driver():
    """Get Neo4j driver connection"""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    return driver

def get_graph_stats(session_id=None):
    """Get statistics about the knowledge graph"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if session_id:
                # Count nodes
                node_count = session.run("MATCH (n:Entity) WHERE n.session_id = $session_id RETURN count(n) as count", session_id=session_id).single()["count"]
                
                # Count relationships
                rel_count = session.run("MATCH (n:Entity)-[r:RELATION]->(m:Entity) WHERE n.session_id = $session_id AND m.session_id = $session_id RETURN count(r) as count", session_id=session_id).single()["count"]
                
                # Get unique relation types
                rel_types = session.run("""
                    MATCH (n:Entity)-[r:RELATION]->(m:Entity)
                    WHERE n.session_id = $session_id AND m.session_id = $session_id
                    RETURN DISTINCT r.type as rel_type, count(*) as count
                    ORDER BY count DESC
                    LIMIT 10
                """, session_id=session_id).data()
            else:
                # Count nodes
                node_count = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
                
                # Count relationships
                rel_count = session.run("MATCH ()-[r:RELATION]->() RETURN count(r) as count").single()["count"]
                
                # Get unique relation types
                rel_types = session.run("""
                    MATCH ()-[r:RELATION]->()
                    RETURN DISTINCT r.type as rel_type, count(*) as count
                    ORDER BY count DESC
                    LIMIT 10
                """).data()
            
            return {
                "nodes": node_count,
                "relationships": rel_count,
                "relation_types": rel_types
            }
    finally:
        driver.close()

def clear_database(session_id=None):
    """Clear all nodes and relationships from the database"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if session_id:
                session.run("MATCH (n) WHERE n.session_id = $session_id DETACH DELETE n", session_id=session_id)
            else:
                session.run("MATCH (n) DETACH DELETE n")
            return True
    except Exception as e:
        print(f"Error clearing database: {e}")
        return False
    finally:
        driver.close()

def get_graph_sample(limit: int = 100, session_id=None):
    """Get a sample of nodes and relationships for visualization"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if session_id:
                result = session.run(f"""
                    MATCH (h:Entity)-[r:RELATION]->(t:Entity)
                    WHERE h.session_id = $session_id AND t.session_id = $session_id
                    RETURN h.name as head, r.type as relation, t.name as tail
                    LIMIT {limit}
                """, session_id=session_id).data()
            else:
                result = session.run(f"""
                    MATCH (h:Entity)-[r:RELATION]->(t:Entity)
                    RETURN h.name as head, r.type as relation, t.name as tail
                    LIMIT {limit}
                """).data()
            
            return result
    finally:
        driver.close()

def get_entity_connections(entity_name: str, depth: int = 2, limit: int = 50, session_id=None):
    """Get connections for a specific entity"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if session_id:
                result = session.run(f"""
                    MATCH path = (start:Entity {{name: $entity_name}})-[*1..{depth}]-(connected:Entity)
                    WHERE start.name <> connected.name AND start.session_id = $session_id AND connected.session_id = $session_id
                    RETURN DISTINCT connected.name as entity, 
                           length(path) as distance
                    LIMIT {limit}
                """, entity_name=entity_name, session_id=session_id).data()
            else:
                result = session.run(f"""
                    MATCH path = (start:Entity {{name: $entity_name}})-[*1..{depth}]-(connected:Entity)
                    WHERE start.name <> connected.name
                    RETURN DISTINCT connected.name as entity, 
                           length(path) as distance
                    LIMIT {limit}
                """, entity_name=entity_name).data()
            
            return result
    finally:
        driver.close()

def create_networkx_graph(triples: List[Dict]) -> nx.DiGraph:
    """Create a NetworkX graph from triples"""
    G = nx.DiGraph()
    
    for triple in triples:
        head = triple.get('head', '')
        tail = triple.get('tail', '')
        relation = triple.get('relation', '')
        
        if head and tail:
            G.add_node(head, label=head)
            G.add_node(tail, label=tail)
            G.add_edge(head, tail, label=relation, relation=relation)
    
    return G

def visualize_graph_pyvis(triples: List[Dict], output_path: str = "graph.html", height: str = "800px", width: str = "100%") -> str:
    """Create an interactive graph visualization using Pyvis"""
    net = Network(height=height, width=width, directed=True, bgcolor="#222222", font_color="white")
    
    # Add nodes and edges
    nodes_set = set()
    for triple in triples:
        head = triple.get('head', '')
        tail = triple.get('tail', '')
        relation = triple.get('relation', '')
        
        if head and tail:
            if head not in nodes_set:
                net.add_node(head, label=head, color="#97c2fc", size=20)
                nodes_set.add(head)
            if tail not in nodes_set:
                net.add_node(tail, label=tail, color="#97c2fc", size=20)
                nodes_set.add(tail)
            
            net.add_edge(head, tail, label=relation, color="#848484", width=2)
    
    # Configure physics
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "stabilization": {"enabled": true, "iterations": 100},
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.1,
          "springLength": 200,
          "springConstant": 0.05
        }
      }
    }
    """)
    
    net.save_graph(output_path)
    return output_path

def query_graph_cypher(query: str, session_id=None) -> List[Dict]:
    """Execute a Cypher query and return results"""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if session_id:
                # This is a bit hacky, but for simple queries it works. 
                # Ideally, the query itself should be constructed with session_id.
                # For now, we'll assume the caller handles it or we pass it as a parameter if the query supports it.
                result = session.run(query, session_id=session_id).data()
            else:
                result = session.run(query).data()
            return result
    finally:
        driver.close()






