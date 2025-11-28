import streamlit as st
import os
import json
import tempfile
import time
import uuid
from pathlib import Path
from agents import get_crew, generate_research_topics
from tools import cypher_chain, graph, initialize_components
from extract_graph import process_pdf_file
from populate_Graph import populate_neo4j
from graph_utils import (
    get_graph_stats, 
    get_graph_sample, 
    visualize_graph_pyvis,
    get_entity_connections,
    clear_database,
    cleanup_old_data
)

# Page configuration
st.set_page_config(
    page_title="🧬 AI Research Knowledge Graph",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clear database on startup (only once per session)
if 'db_cleared' not in st.session_state:
    try:
        # 1. Clear current session data (just in case)
        if clear_database(st.session_state.session_id):
            print(f"✅ Database cleared for session {st.session_state.session_id}")
        else:
            print("❌ Failed to clear database on startup")
            
        # 2. Run TTL Cleanup (delete orphaned data > 24 hours old)
        # This runs once per user session start, keeping the DB clean
        deleted = cleanup_old_data(hours=24)
        if deleted > 0:
            print(f"🧹 Auto-Cleanup: Removed {deleted} old nodes.")
            
        st.session_state.db_cleared = True
    except Exception as e:
        print(f"Error clearing database: {e}")

# Custom CSS for beautiful styling
# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Main Layout & Background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Headers */
    .main-header {
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(120deg, #FF4B4B 0%, #FF9068 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 0 30px rgba(255, 75, 75, 0.3);
    }
    
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #E0E0E0;
    }
    
    /* Cards & Containers */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 16px;
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #FF4B4B;
    }
    
    .info-box {
        background: rgba(38, 39, 48, 0.5);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #FF4B4B;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF9068 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255, 75, 75, 0.4);
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 8px;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #FF4B4B;
        box-shadow: 0 0 0 1px #FF4B4B;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #9CA3AF;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        color: #FF4B4B;
        border-bottom: 2px solid #FF4B4B;
    }
    
    /* HIDE STREAMLIT DEFAULT ELEMENTS */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'graph_created' not in st.session_state:
    st.session_state.graph_created = False
if 'triples_data' not in st.session_state:
    st.session_state.triples_data = []
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = ""
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'processed_papers' not in st.session_state:
    st.session_state.processed_papers = {}  # Dict to store metadata: {filename: {summary, domain}}

# Optimize initialization
@st.cache_resource
def init_app_components():
    """Initialize global components once"""
    try:
        initialize_components()
        return True
    except Exception as e:
        print(f"Initialization error: {e}")
        return False

# Run initialization
init_app_components()


# Sidebar
with st.sidebar:
    st.title("🧬 Navigation")
    st.markdown("---")
    
    # Connection status
    try:
        stats = get_graph_stats(session_id=st.session_state.session_id)
        st.success("✅ Neo4j Connected")
        st.metric("Nodes", stats.get('nodes', 0))
        st.metric("Relationships", stats.get('relationships', 0))
        st.session_state.graph_created = True
        
        if stats.get('nodes', 0) == 0:
            if st.session_state.get('db_cleared', False):
                st.info("🧹 Database cleared on startup. Ready for new data!")
            st.info("📝 No data in graph yet. Upload and process PDFs to get started!")
    except Exception as e:
        st.error(f"❌ Neo4j Connection Failed")
        st.info("Please ensure Neo4j is running and credentials are set in .env")
        st.session_state.graph_created = False
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    if st.session_state.graph_created:
        try:
            stats = get_graph_stats(session_id=st.session_state.session_id)
            st.write(f"**Total Nodes:** {stats['nodes']}")
            st.write(f"**Total Relationships:** {stats['relationships']}")
            if stats['relation_types']:
                st.write("**Top Relations:**")
                for rel in stats['relation_types'][:5]:
                    st.write(f"  - {rel['rel_type']}: {rel['count']}")
        except:
            pass

# Main header
st.markdown('<h1 class="main-header">🧬 AI Research Knowledge Graph</h1>', unsafe_allow_html=True)
st.markdown("### Transform Research Papers into Interactive Knowledge Graphs")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Upload & Process", 
    "🔍 Query Graph", 
    "📊 Visualize", 
    "🤖 AI Scientists"
])

# ========== TAB 1: UPLOAD & PROCESS ==========
with tab1:
    st.header("📤 Upload Research Papers")
    st.markdown("Upload PDF files of research papers to extract knowledge and build your graph.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="You can upload multiple PDF files at once"
        )
    
    with col2:
        st.markdown("### 📋 Uploaded Files")
        if uploaded_files:
            for file in uploaded_files:
                st.write(f"📄 {file.name} ({file.size / 1024:.1f} KB)")
        else:
            st.info("No files uploaded yet")
    
    if uploaded_files:
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Process PDFs & Extract Knowledge", use_container_width=True):
                if not st.session_state.graph_created:
                    st.error("❌ Please connect to Neo4j first. Check your connection in the sidebar.")
                else:
                    all_triples = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, uploaded_file in enumerate(uploaded_files):
                        status_text.text(f"Processing {uploaded_file.name}... ({idx+1}/{len(uploaded_files)})")
                        
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        try:
                            # Process PDF
                            def progress_callback(msg):
                                status_text.text(msg)
                            
                            file_triples, domain, summary = process_pdf_file(
                                tmp_path, 
                                filename=uploaded_file.name,
                                progress_callback=progress_callback
                            )
                            
                            # Store metadata
                            st.session_state.processed_papers[uploaded_file.name] = {
                                'domain': domain,
                                'summary': summary
                            }
                            
                            # Store domain and generate relevant queries if not already done
                            if domain and domain != "Unknown":
                                st.session_state.current_domain = domain
                                # Generate dynamic queries based on domain
                                try:
                                    from tools import llm
                                    prompt = f"Generate 5 short, interesting natural language questions for a knowledge graph about {domain}. Return only the questions as a JSON list of strings."
                                    response = llm.invoke(prompt)
                                    import re
                                    json_match = re.search(r'\[.*?\]', str(response.content), re.DOTALL)
                                    if json_match:
                                        st.session_state.dynamic_queries = json.loads(json_match.group())
                                except:
                                    pass # Fallback to default queries if generation fails
                            
                            all_triples.extend(file_triples)
                            progress_bar.progress((idx + 1) / len(uploaded_files))
                            
                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {e}")
                        finally:
                            # Clean up temp file
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    
                    if all_triples:
                        st.session_state.triples_data = all_triples
                        
                        # Save to JSON
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_json:
                            json.dump(all_triples, tmp_json, indent=2)
                            tmp_json_path = tmp_json.name
                        
                        status_text.text("💾 Saving to Neo4j...")
                        
                        try:
                            success, message, count = populate_neo4j(tmp_json_path, session_id=st.session_state.session_id)
                            if success:
                                st.success(f"✅ Successfully processed {len(uploaded_files)} file(s) and extracted {len(all_triples)} knowledge triples!")
                                st.balloons()
                                
                                # Clean up
                                if os.path.exists(tmp_json_path):
                                    os.unlink(tmp_json_path)
                                    
                                # Refresh page to show updated stats
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Error saving to Neo4j: {message}")
                        except Exception as e:
                            st.error(f"Error saving to Neo4j: {e}")
                    else:
                        st.warning("⚠️ No triples extracted from the uploaded files.")
                        st.info("💡 Tips: Make sure the PDFs contain extractable text (not just images). Try with research papers that have clear text content.")
            
            # Display Summaries
            if st.session_state.processed_papers:
                st.markdown("### 📝 Processed Papers & Summaries")
                for filename, data in st.session_state.processed_papers.items():
                    with st.expander(f"📄 {filename} ({data.get('domain', 'Unknown')})"):
                        st.markdown(f"**Summary:**\n{data.get('summary', 'No summary available.')}")
        
        with col2:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.uploaded_files = []
                st.session_state.triples_data = []
                st.rerun()

# ========== TAB 2: QUERY GRAPH ==========
with tab2:
    st.header("🔍 Query Your Knowledge Graph")
    st.markdown("Ask questions in natural language to explore your knowledge graph.")
    
    if not st.session_state.graph_created:
        st.warning("⚠️ Please ensure Neo4j is connected. Check the sidebar for connection status.")
    else:
        # Example queries
        st.markdown("### 💡 Example Queries")
        
        # Use dynamic queries if available, otherwise defaults
        default_queries = [
            "What are all the entities related to Alzheimer's disease?",
            "List all proteins and their relationships",
            "What mechanisms are associated with neuroinflammation?",
            "Show me all relationships involving amyloid",
            "What are the connections between different diseases?"
        ]
        
        example_queries = st.session_state.get('dynamic_queries', default_queries)
        
        if st.session_state.get('current_domain'):
            st.info(f"🎯 Detected Domain: **{st.session_state.current_domain}**")
        
        cols = st.columns(3)
        for i, example in enumerate(example_queries):
            with cols[i % 3]:
                if st.button(f"💬 {example[:40]}...", key=f"example_{i}", use_container_width=True):
                    st.session_state.query_text = example
        
        st.markdown("---")
        
        # Query input
        query = st.text_input(
            "Enter your question:",
            value=st.session_state.get('query_text', ''),
            placeholder="e.g., What targets LRRK2? or List all proteins related to Parkinson's disease"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            search_button = st.button("🔍 Search", use_container_width=True)
        
        if search_button and query:
            with st.spinner("🤔 Analyzing your question and querying the graph..."):
                try:
                    # Ensure components are initialized
                    if cypher_chain is None:
                        initialize_components()
                    
                    # Check if graph has data
                    try:
                        from graph_utils import get_graph_stats
                        stats = get_graph_stats(session_id=st.session_state.session_id)
                        node_count = stats.get('nodes', 0)
                        rel_count = stats.get('relationships', 0)
                        
                        if node_count == 0:
                            st.warning("⚠️ The knowledge graph is empty!")
                            st.info("📝 Please upload and process PDF files first to populate the graph with data.")
                            st.stop()
                        else:
                            st.info(f"📊 Graph has {node_count} nodes and {rel_count} relationships")
                    except Exception as stats_error:
                        st.warning(f"⚠️ Could not check graph stats: {stats_error}")
                    
                    # Enhance question with schema context
                    from tools import fix_cypher_query, try_direct_query, generate_answer_from_results
                    enhanced_question = f"""
                    Graph Schema: Nodes have label 'Entity' with property 'name'. Relationships have type 'RELATION' with property 'type'.
                    Pattern: (n:Entity {{name: 'entity_name'}})-[r:RELATION]-(m:Entity {{name: 'entity_name'}})
                    
                    Question: {query}
                    
                    Generate a Cypher query using the Entity label and RELATION type.
                    """
                    
                    # Try different invocation formats
                    try:
                        response = cypher_chain.invoke({"query": enhanced_question})
                    except:
                        try:
                            response = cypher_chain.invoke({"query": query})
                        except:
                            # Fallback to direct string input
                            response = cypher_chain.invoke(query)
                    
                    # Handle response format
                    if isinstance(response, dict):
                        answer = response.get('result', response.get('answer', str(response)))
                        intermediate = response.get('intermediate_steps', [])
                    else:
                        answer = str(response)
                        intermediate = []
                    
                    # Check if query failed and try to fix it
                    answer_lower = answer.lower() if answer else ""
                    if any(phrase in answer_lower for phrase in ["i don't know", "i do not know", "cannot answer", "no information", "unable to", "no results"]) or not answer:
                        # Try to fix and re-execute the query
                        fixed_query_used = False
                        if intermediate:
                            for step in intermediate:
                                if isinstance(step, dict) and 'query' in step:
                                    original_query = step['query']
                                    fixed_query = fix_cypher_query(original_query)
                                    
                                    if fixed_query != original_query:
                                        # Re-execute with fixed query
                                        try:
                                            from tools import graph
                                            with graph._driver.session() as session:
                                                fixed_result = session.run(fixed_query).data()
                                                if fixed_result:
                                                    # Generate answer from fixed results
                                                    answer = generate_answer_from_results(query, fixed_result, None)
                                                    if answer:
                                                        fixed_query_used = True
                                                        st.success("✅ Found Results! (Query was automatically fixed)")
                                                        st.markdown("### 📝 Answer")
                                                        st.markdown(answer)
                                                        with st.expander("🔍 See Fixed Cypher Query"):
                                                            st.code(f"Original: {original_query}", language="cypher")
                                                            st.code(f"Fixed: {fixed_query}", language="cypher")
                                                        break
                                        except Exception as fix_error:
                                            pass
                        
                        if not fixed_query_used:
                            # Try direct query with proper schema
                            from tools import graph, llm
                            direct_answer = try_direct_query(query, graph, llm)
                            if direct_answer:
                                st.success("✅ Found Results! (Using direct query)")
                                st.markdown("### 📝 Answer")
                                st.markdown(direct_answer)
                            else:
                                st.warning("⚠️ No information found")
                                st.info(f"""
                                💡 **Tips to get better results:**
                                - Make sure you've uploaded and processed PDF files
                                - Try asking about specific entities (e.g., "What is Alzheimer's disease?")
                                - Ask about relationships (e.g., "What proteins interact with tau?")
                                - Use entity names from your uploaded papers
                                
                                **Current graph stats:** {stats.get('nodes', 0)} nodes, {stats.get('relationships', 0)} relationships
                                """)
                                
                                if intermediate:
                                    with st.expander("🔍 See Generated Cypher Query"):
                                        for step in intermediate:
                                            if isinstance(step, dict) and 'query' in step:
                                                st.code(step['query'], language="cypher")
                    else:
                        st.success("✅ Found Results!")
                        st.markdown("### 📝 Answer")
                        st.markdown(answer)
                        
                        # Show Cypher query if available
                        if intermediate:
                            with st.expander("🔍 See Generated Cypher Query"):
                                for step in intermediate:
                                    if isinstance(step, dict) and 'query' in step:
                                        st.code(step['query'], language="cypher")
                    
                except Exception as e:
                    st.error(f"❌ An error occurred: {e}")
                    st.info("💡 Try rephrasing your question or check if the graph has relevant data.")

# ========== TAB 3: VISUALIZE ==========
with tab3:
    st.header("📊 Visualize Knowledge Graph")
    st.markdown("Explore your knowledge graph through interactive visualizations.")
    
    if not st.session_state.graph_created:
        st.warning("⚠️ Please ensure Neo4j is connected and you have processed some PDFs.")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            viz_limit = st.slider("Number of relationships to visualize", 10, 200, 50)
        
        with col2:
            viz_type = st.selectbox(
                "Visualization Type",
                ["Full Graph", "Entity Connections", "Random Sample"]
            )
        
        with col3:
            if st.button("🔄 Generate Visualization", use_container_width=True):
                st.session_state.generate_viz = True
        
        if st.session_state.get('generate_viz', False):
            with st.spinner("🎨 Creating visualization..."):
                try:
                    if viz_type == "Random Sample":
                        triples_data = get_graph_sample(limit=viz_limit, session_id=st.session_state.session_id)
                    elif viz_type == "Full Graph":
                        # Get all relationships (limited)
                        from graph_utils import query_graph_cypher
                        triples_data = query_graph_cypher(f"""
                            MATCH (h:Entity)-[r:RELATION]->(t:Entity)
                            WHERE h.session_id = '{st.session_state.session_id}' AND t.session_id = '{st.session_state.session_id}'
                            RETURN h.name as head, r.type as relation, t.name as tail
                            LIMIT {viz_limit}
                        """, session_id=st.session_state.session_id)
                    else:
                        entity_name = st.text_input("Enter entity name for connections:", key="entity_viz")
                        if entity_name:
                            connections = get_entity_connections(entity_name, limit=viz_limit, session_id=st.session_state.session_id)
                            triples_data = [{"head": entity_name, "relation": "connected_to", "tail": conn['entity']} 
                                           for conn in connections]
                        else:
                            st.info("Please enter an entity name")
                            triples_data = []
                    
                    if triples_data:
                        # Convert to format expected by visualize function
                        triples_list = [
                            {
                                "head": str(t.get('head', '')),
                                "relation": str(t.get('relation', '')),
                                "tail": str(t.get('tail', ''))
                            }
                            for t in triples_data
                            if t.get('head') and t.get('tail')  # Filter out empty entries
                        ]
                        
                        if triples_list:
                            # Create visualization
                            import tempfile
                            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html', dir='.') as tmp_file:
                                tmp_viz_path = tmp_file.name
                            
                            try:
                                visualize_graph_pyvis(
                                    triples_list, 
                                    output_path=tmp_viz_path,
                                    height="800px"
                                )
                                
                                # Display in Streamlit
                                with open(tmp_viz_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                
                                st.components.v1.html(html_content, height=850)
                                
                                st.success(f"✅ Visualization created with {len(triples_list)} relationships!")
                                
                                # Clean up
                                if os.path.exists(tmp_viz_path):
                                    os.unlink(tmp_viz_path)
                            except Exception as viz_error:
                                st.error(f"Error creating visualization: {viz_error}")
                        else:
                            st.info("No valid relationships found for visualization.")
                    else:
                        st.info("No data available for visualization. Please process some PDFs first.")
                        
                except Exception as e:
                    st.error(f"❌ Error creating visualization: {e}")

# ========== TAB 4: AI SCIENTISTS ==========
with tab4:
    st.header("🤖 AI Scientist Crew")
    st.markdown("""
    <div class="info-box">
        <strong>🧪 Deep Research Analysis</strong><br>
        Launch a team of AI agents to analyze your knowledge graph, find novel connections, 
        and generate new research hypotheses. The crew consists of:
        <ul>
            <li><strong>Graph Analyst:</strong> Queries and analyzes the knowledge graph</li>
            <li><strong>Research Connector:</strong> Finds novel connections and relationships</li>
            <li><strong>Lead Scientist:</strong> Generates innovative hypotheses</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.graph_created:
        st.warning("⚠️ Please ensure Neo4j is connected and you have processed some PDFs.")
    else:
        st.markdown("### 🎯 Research Configuration")
        
        col_domain, col_topic = st.columns([1, 2])
        
        with col_domain:
            # Auto-fill domain if detected
            default_domain = st.session_state.get('current_domain', "Scientific Research")
            if default_domain == "Unknown": 
                default_domain = "Scientific Research"
                
            domain_input = st.text_input(
                "Research Domain:",
                value=default_domain,
                help="The broader field of study (e.g., Biology, Computer Science)"
            )
            
        with col_topic:
            research_topic = st.text_input(
                "Specific Topic:",
                placeholder="e.g., Alzheimer's disease mechanisms",
                help="The specific question or topic to investigate"
            )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Launch AI Crew", use_container_width=True):
                if research_topic:
                    with st.spinner("🤖 AI Scientists are working... This may take 1-3 minutes..."):
                        try:
                            # Create progress indicators
                            progress_bar = st.progress(0)
                            status_container = st.container()
                            
                            with status_container:
                                st.info("🔬 **Graph Analyst** is querying the knowledge graph...")
                                progress_bar.progress(20)
                                time.sleep(0.5)
                                
                                st.info("🔗 **Research Connector** is finding novel connections...")
                                progress_bar.progress(50)
                                time.sleep(0.5)
                                
                                st.info("💡 **Lead Scientist** is generating hypotheses...")
                                progress_bar.progress(80)
                            
                            # Launch crew
                            crew = get_crew(research_topic, domain=domain_input)
                            result = crew.kickoff()
                            
                            progress_bar.progress(100)
                            
                            st.success("✅ Research Complete!")
                            st.markdown("---")
                            
                            # Display results
                            st.subheader("🔬 Analysis Results")
                            st.markdown(result)
                            
                            # Save results option
                            if st.button("💾 Download Results"):
                                st.download_button(
                                    label="📥 Download as Text",
                                    data=result,
                                    file_name=f"research_analysis_{research_topic.replace(' ', '_')}.txt",
                                    mime="text/plain"
                                )
                            
                        except Exception as e:
                            error_msg = str(e)
                            st.error(f"❌ Error: {error_msg}")
                            
                            # Provide specific guidance based on error type
                            if "litellm" in error_msg.lower() or "LLM Provider" in error_msg:
                                st.info("""
                                💡 **CrewAI Configuration Issue**: 
                                - Make sure your GOOGLE_API_KEY is set correctly in .env
                                - The model 'gemini-flash-latest' should work with your paid tier
                                - Try restarting the application
                                """)
                            elif "rate limit" in error_msg.lower() or "429" in error_msg or "quota" in error_msg:
                                st.info("💡 Rate limit exceeded. Please wait a few minutes and try again.")
                            else:
                                st.info("💡 If this persists, check your API key and ensure Neo4j is connected.")
                else:
                    st.warning("⚠️ Please enter a research topic first.")
        
        with col2:
            st.markdown("### 📚 Example Topics")
            
            # Check if we need to generate new topics
            if 'dynamic_topics' not in st.session_state or st.session_state.get('last_processed_count', 0) != len(st.session_state.processed_papers):
                
                # Get context from processed papers
                if st.session_state.processed_papers:
                    context_summaries = "\n".join([f"- {p['summary']}" for p in st.session_state.processed_papers.values() if p.get('summary')])
                    current_domain = st.session_state.get('current_domain', "Scientific Research")
                    
                    if context_summaries:
                        with st.spinner("🧠 Generating relevant research topics..."):
                            try:
                                st.session_state.dynamic_topics = generate_research_topics(current_domain, context_summaries)
                                st.session_state.last_processed_count = len(st.session_state.processed_papers)
                            except Exception as e:
                                print(f"Error generating topics: {e}")
                                # Fallback
                                st.session_state.dynamic_topics = [
                                    "Alzheimer's disease and tau pathology",
                                    "Neuroinflammation mechanisms",
                                    "Amyloid beta aggregation",
                                    "Protein-protein interactions in neurodegeneration",
                                    "Genetic factors in dementia"
                                ]
                    else:
                         st.session_state.dynamic_topics = [
                            "Alzheimer's disease and tau pathology",
                            "Neuroinflammation mechanisms",
                            "Amyloid beta aggregation",
                            "Protein-protein interactions in neurodegeneration",
                            "Genetic factors in dementia"
                        ]
                else:
                    # Default if no papers
                    st.session_state.dynamic_topics = [
                        "Alzheimer's disease and tau pathology",
                        "Neuroinflammation mechanisms",
                        "Amyloid beta aggregation",
                        "Protein-protein interactions in neurodegeneration",
                        "Genetic factors in dementia"
                    ]
            
            example_topics = st.session_state.dynamic_topics
            
            for topic in example_topics:
                if st.button(f"📌 {topic}", key=f"topic_{topic}", use_container_width=True):
                    st.session_state.research_topic = topic
                    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🧬 AI Research Knowledge Graph System | Powered by Gemini AI, Neo4j, and CrewAI</p>
    <p>Transform your research papers into interactive knowledge graphs</p>
</div>
""", unsafe_allow_html=True)
