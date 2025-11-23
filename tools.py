import os
import time
import re
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

# 1. Setup Graph Connection
def get_graph():
    """Get or create Neo4j graph connection"""
    try:
        graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
        return graph
    except Exception as e:
        raise Exception(f"Failed to connect to Neo4j: {e}")

# Initialize graph connection (lazy loading to avoid errors on import)
graph = None
llm = None
cypher_chain = None

def initialize_components():
    """Initialize graph, LLM, and chain components lazily"""
    global graph, llm, cypher_chain
    
    if graph is None:
        graph = get_graph()
    
    if llm is None:
        # 2. Define the Chain (The "Engine") with retry configuration
        # Use correct model name for paid tier
        llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest", 
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=5,
            request_timeout=120
        )
    
    if cypher_chain is None:
        # Create the Cypher QA Chain with better configuration
        try:
            # Check if graph has data first
            try:
                with graph._driver.session() as session:
                    node_count = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
                    if node_count == 0:
                        print("⚠️ Warning: Graph is empty. Please upload and process PDFs first.")
            except:
                pass  # Continue anyway
            
            # Refresh graph schema to ensure it's up to date
            try:
                graph.refresh_schema()
            except:
                pass  # Continue if refresh fails
            
            cypher_chain = GraphCypherQAChain.from_llm(
                llm=llm,
                graph=graph,
                verbose=True,
                return_intermediate_steps=True,
                allow_dangerous_requests=True,
                return_direct=False
            )
        except Exception as e:
            # Fallback: try without allow_dangerous_requests if it's not supported
            try:
                cypher_chain = GraphCypherQAChain.from_llm(
                    llm=llm,
                    graph=graph,
                    verbose=True,
                    return_intermediate_steps=True,
                    return_direct=False
                )
            except Exception as e2:
                raise Exception(f"Failed to create Cypher chain: {e2}")

# Initialize on first import (but handle errors gracefully)
try:
    initialize_components()
except Exception as e:
    # Don't fail on import - will be initialized when needed
    pass

# 3. Create the Tool for CrewAI (The "Wrapper")
class GraphTools:
    @tool("Graph RAG Search")
    def query_graph(question: str) -> str:
        """
        Useful to query the knowledge graph for relationships, connections, 
        and specific facts. Input should be a specific question about the knowledge graph.
        
        Args:
            question: A natural language question about entities, relationships, or concepts in the graph.
        
        Returns:
            A string containing the answer to the question based on the knowledge graph.
        """
        global cypher_chain
        
        # Initialize if not already done
        if cypher_chain is None:
            initialize_components()
            
        # Get session ID from Streamlit state if available
        import streamlit as st
        try:
            session_id = st.session_state.get('session_id')
        except:
            session_id = None
        
        max_retries = 3
        base_delay = 5  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                # Check if graph has data (filtered by session)
                try:
                    with graph._driver.session() as session:
                        if session_id:
                            node_count = session.run("MATCH (n:Entity) WHERE n.session_id = $session_id RETURN count(n) as count", session_id=session_id).single()["count"]
                        else:
                            node_count = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
                            
                        if node_count == 0:
                            return "The knowledge graph is empty. Please upload and process PDF files first to populate the graph with data."
                except:
                    pass
                
                # Enhance question with schema context for better query generation
                # CRITICAL: Enforce session isolation in the prompt
                session_filter = f"WHERE n.session_id = '{session_id}' AND m.session_id = '{session_id}'" if session_id else ""
                
                enhanced_question = f"""
                Graph Schema: Nodes have label 'Entity' with property 'name' and 'session_id'. Relationships have type 'RELATION' with property 'type' and 'session_id'.
                
                IMPORTANT: You must ONLY query data belonging to the current session.
                Current Session ID: {session_id}
                
                Pattern: (n:Entity {{name: 'entity_name'}})-[r:RELATION]-(m:Entity {{name: 'entity_name'}})
                ALWAYS include the session filter: {session_filter}
                
                Question: {question}
                
                Generate a Cypher query using the Entity label and RELATION type.
                Ensure EVERY MATCH clause filters by session_id = '{session_id}'.
                """
                
                # Try different invocation formats
                try:
                    result = cypher_chain.invoke({"query": enhanced_question})
                except:
                    try:
                        result = cypher_chain.invoke({"query": question})
                    except:
                        # Fallback to direct string input
                        result = cypher_chain.invoke(question)
                
                # Handle both old and new response formats
                if isinstance(result, dict):
                    answer = result.get('result', result.get('answer', ''))
                    intermediate = result.get('intermediate_steps', [])
                    
                    # Check if query failed and try to fix it
                    answer_lower = answer.lower() if answer else ""
                    if any(phrase in answer_lower for phrase in ["i don't know", "i do not know", "cannot answer", "no information", "unable to", "no results"]) or not answer:
                        # Try to fix and re-execute the query
                        if intermediate:
                            for step in intermediate:
                                if isinstance(step, dict) and 'query' in step:
                                    original_query = step['query']
                                    fixed_query = fix_cypher_query(original_query)
                                    
                                    if fixed_query != original_query:
                                        # Re-execute with fixed query
                                        try:
                                            with graph._driver.session() as session:
                                                fixed_result = session.run(fixed_query).data()
                                                if fixed_result:
                                                    # Generate answer from fixed results
                                                    answer = generate_answer_from_results(question, fixed_result, llm)
                                                    if answer:
                                                        return answer
                                        except Exception as fix_error:
                                            # If fixed query fails, try direct query
                                            pass
                        
                        # Try direct query with proper schema
                        direct_answer = try_direct_query(question, graph, llm)
                        if direct_answer:
                            return direct_answer
                    
                    if not answer or answer.strip() == "":
                        answer = str(result)
                    
                    # Final check for empty answers
                    if not answer or "don't know" in answer.lower() or "no information" in answer.lower():
                        direct_answer = try_direct_query(question, graph, llm)
                        if direct_answer:
                            return direct_answer
                        return f"I couldn't find information about '{question}' in the knowledge graph. Make sure you've uploaded and processed PDF files, and try asking about specific entities, relationships, or concepts from your research papers."
                    
                    return answer
                else:
                    answer = str(result)
                    if not answer or "don't know" in answer.lower():
                        # Try direct query
                        direct_answer = try_direct_query(question, graph, llm)
                        if direct_answer:
                            return direct_answer
                        return f"I couldn't find information about '{question}' in the knowledge graph. Please ensure you've uploaded PDFs and processed them, then try asking about specific entities or relationships."
                    return answer
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a rate limit error
                if "resourceexhausted" in error_str or "429" in error_str or "quota" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 5s, 10s, 20s
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        return f"Rate limit exceeded. Please wait a few minutes and try again. Error: {e}"
                else:
                    return f"Error querying graph: {e}"
        
        return "Failed to query graph after multiple retries."

def fix_cypher_query(query: str) -> str:
    """Fix common Cypher query issues to match our graph schema"""
    if not query:
        return query
    
    original_query = query
    
    # Fix pattern: (tau {name: 'tau'}) -> (n:Entity {name: 'tau'})
    # Match patterns like (word {name: 'value'}) where word might be an entity name
    def fix_node_pattern(match):
        var_name = match.group(1)
        prop_value = match.group(2)
        # If var_name looks like an entity name (not a typical variable), fix it
        if var_name and not var_name.startswith('_') and len(var_name) > 2:
            # Check if it's likely an entity name vs variable
            if var_name.lower() == prop_value.lower() or var_name[0].isupper():
                # This is likely an entity name, use Entity label
                return f'(n:Entity {{name: "{prop_value}"}})'
            else:
                # This might be a variable, but still add Entity label
                return f'({var_name}:Entity {{name: "{prop_value}"}})'
        return match.group(0)
    
    # Pattern 1: (word {name: 'value'})
    query = re.sub(r'\((\w+)\s*\{name:\s*[\'"]([^\'"]+)[\'"]\}\)', fix_node_pattern, query)
    
    # Pattern 2: (word) where word might be an entity - harder to fix automatically
    # We'll handle this in the direct query function
    
    # Ensure relationships use RELATION type if not specified
    # Fix: [] -> [:RELATION]
    query = re.sub(r'\[(\w*)\]', lambda m: f'[{m.group(1) or "r"}:RELATION]' if not m.group(1) or ':' not in m.group(1) else m.group(0), query)
    
    # Fix: Ensure all nodes with name property have Entity label
    query = re.sub(r'\(([a-zA-Z_]\w*)\s*\{name:', r'(\1:Entity {name:', query)
    
    return query

def try_direct_query(question: str, graph, llm):
    """Try a direct query with proper schema and session isolation"""
    import streamlit as st
    try:
        session_id = st.session_state.get('session_id')
    except:
        session_id = None
        
    question_lower = question.lower()
    
    # Pattern 1: "What X interact with Y?" or "What proteins interact with tau?"
    if "interact" in question_lower:
        # Extract entity name (usually the last significant word before "interact" or after)
        # For "What proteins interact with tau?" -> "tau"
        match = re.search(r'(?:with|to|and)\s+([a-zA-Z]+)', question, re.IGNORECASE)
        if match:
            entity_name = match.group(1)
            try:
                with graph._driver.session() as session:
                    # Try exact match first
                    query = """
                        MATCH (e1:Entity)-[r:RELATION]-(e2:Entity)
                        WHERE (toLower(e1.name) = toLower($entity) OR toLower(e2.name) = toLower($entity))
                    """
                    if session_id:
                        query += " AND e1.session_id = $session_id AND e2.session_id = $session_id"
                        
                    query += """
                        RETURN DISTINCT 
                            CASE WHEN toLower(e1.name) = toLower($entity) THEN e2.name ELSE e1.name END as connected_entity,
                            r.type as relation,
                            CASE WHEN toLower(e1.name) = toLower($entity) THEN e1.name ELSE e2.name END as source_entity
                        LIMIT 20
                    """
                    
                    result = session.run(query, entity=entity_name, session_id=session_id).data()
                    
                    if result:
                        return generate_answer_from_results(question, result, llm)
                    
                    # Try partial match
                    query = """
                        MATCH (e1:Entity)-[r:RELATION]-(e2:Entity)
                        WHERE (toLower(e1.name) CONTAINS toLower($entity) OR toLower(e2.name) CONTAINS toLower($entity))
                    """
                    if session_id:
                        query += " AND e1.session_id = $session_id AND e2.session_id = $session_id"
                        
                    query += """
                        RETURN DISTINCT 
                            CASE WHEN toLower(e1.name) CONTAINS toLower($entity) THEN e2.name ELSE e1.name END as connected_entity,
                            r.type as relation
                        LIMIT 20
                    """
                    
                    result = session.run(query, entity=entity_name, session_id=session_id).data()
                    
                    if result:
                        return generate_answer_from_results(question, result, llm)
            except Exception as e:
                pass
    
    # Pattern 2: "What is X?" or "Tell me about X"
    if "what is" in question_lower or "tell me about" in question_lower or "what are" in question_lower:
        # Extract entity name
        match = re.search(r'(?:what is|tell me about|what are)\s+([a-zA-Z\s]+)', question_lower)
        if match:
            entity_name = match.group(1).strip()
            try:
                with graph._driver.session() as session:
                    query = """
                        MATCH (e:Entity)-[r:RELATION]-(connected:Entity)
                        WHERE toLower(e.name) CONTAINS toLower($entity)
                    """
                    if session_id:
                        query += " AND e.session_id = $session_id AND connected.session_id = $session_id"
                        
                    query += """
                        RETURN e.name as entity, r.type as relation, connected.name as connected_to
                        LIMIT 15
                    """
                    
                    result = session.run(query, entity=entity_name, session_id=session_id).data()
                    
                    if result:
                        return generate_answer_from_results(question, result, llm)
            except:
                pass
    
    # Pattern 3: General entity search - find entities mentioned in question
    # Extract potential entity names (capitalized words or quoted strings)
    potential_entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', question)
    potential_entities.extend(re.findall(r'["\']([^"\']+)["\']', question))
    
    for entity in potential_entities[:3]:  # Try first 3 potential entities
        if len(entity) > 2:
            try:
                with graph._driver.session() as session:
                    # Search for entity and its relationships
                    query = """
                        MATCH (e:Entity)-[r:RELATION]-(other:Entity)
                        WHERE toLower(e.name) CONTAINS toLower($entity)
                    """
                    if session_id:
                        query += " AND e.session_id = $session_id AND other.session_id = $session_id"
                        
                    query += """
                        RETURN e.name as entity, r.type as relation, other.name as related_entity
                        LIMIT 15
                    """
                    
                    result = session.run(query, entity=entity, session_id=session_id).data()
                    
                    if result:
                        return generate_answer_from_results(question, result, llm)
            except:
                pass
    
    return None

def generate_answer_from_results(question: str, results: list, llm=None):
    """Generate a natural language answer from Cypher query results"""
    if not results:
        return None
    
    # Format results for better readability
    formatted_results = []
    for r in results[:10]:  # Limit to 10 results
        if isinstance(r, dict):
            # Format dictionary results nicely
            parts = []
            for key, value in r.items():
                if value:
                    parts.append(f"{key}: {value}")
            formatted_results.append(" | ".join(parts))
        else:
            formatted_results.append(str(r))
    
    results_text = "\n".join(formatted_results)
    
    # Try using LLM if available
    if llm:
        prompt = f"""Based on the following graph query results, answer the question: {question}

Query Results:
{results_text}

Provide a clear, concise answer based on these results."""
        
        try:
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            return answer
        except:
            pass
    
    # Fallback: format results manually
    if "interact" in question.lower() or "interaction" in question.lower():
        # Format interaction results
        entities = []
        for r in results[:10]:
            if isinstance(r, dict):
                entity = r.get('connected_entity') or r.get('related_entity') or r.get('entity2')
                relation = r.get('relation') or r.get('type')
                if entity:
                    entities.append(f"{entity} ({relation})" if relation else entity)
        
        if entities:
            return f"Found {len(results)} interaction(s). Entities that interact: {', '.join(entities[:10])}"
    
    # Generic formatting
    if len(results) == 1:
        result = results[0]
        if isinstance(result, dict):
            return f"Found: {', '.join([f'{k}={v}' for k, v in result.items() if v])}"
        return f"Found: {result}"
    else:
        # Summarize multiple results
        summary_items = []
        for r in results[:5]:
            if isinstance(r, dict):
                # Extract key information
                entity = r.get('entity') or r.get('connected_entity') or r.get('name', '')
                relation = r.get('relation') or r.get('type', '')
                if entity:
                    summary_items.append(entity)
        
        if summary_items:
            return f"Found {len(results)} result(s). Examples: {', '.join(summary_items)}"
        else:
            return f"Found {len(results)} result(s). {results_text[:200]}"