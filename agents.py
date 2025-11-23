import os
import time
from crewai import Agent, Task, Crew, Process, LLM as CrewLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import GraphTools # Import the tool we just made
from dotenv import load_dotenv

load_dotenv()

# Define the LLM for CrewAI
# Use CrewAI's LLM class with correct format for Gemini
# With google-genai provider installed, use the correct format
try:
    # Option 1: Use CrewAI's LLM class with google-genai provider
    llm = CrewLLM(
        model="gemini/gemini-flash-latest",  # Litellm format: provider/model
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.2
    )
except Exception as e:
    # Option 2: Try with just model name (some versions work this way)
    try:
        llm = CrewLLM(
            model="gemini-flash-latest",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2
        )
    except:
        # Option 3: Fallback to LangChain LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            verbose=True,
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=5,
            request_timeout=120
        )

# --- AGENTS ---

# 1. The Analyst (Has access to the Graph Tool)
analyst = Agent(
    role='Senior Graph Analyst',
    goal='Query the knowledge graph to find relevant facts and relationships about the given research topic',
    backstory="""You are an expert data scientist and graph database specialist. 
    You have deep knowledge across multiple research domains, BUT you strictly rely on the provided knowledge graph for your analysis.
    You verify every fact by checking the graph database and provide comprehensive summaries of relationships and connections found ONLY in the graph.
    Do not hallucinate or use external knowledge not present in the graph.""",
    tools=[GraphTools.query_graph],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# 2. The Scientist (Logic & Hypothesis)
scientist = Agent(
    role='Lead Research Scientist',
    goal='Generate novel scientific hypotheses and identify new research directions based ONLY on graph data analysis',
    backstory="""You are a visionary researcher with decades of experience. 
    You excel at connecting disparate pieces of information to form novel hypotheses. 
    However, your hypotheses must be strictly grounded in the evidence provided by the Analyst and Connector from the knowledge graph.
    You must cite the specific graph connections that support your hypotheses.
    Do not introduce external facts that are not supported by the graph data.""",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# 3. The Connector (Finds new connections)
connector = Agent(
    role='Research Connector',
    goal='Identify novel connections and relationships between entities in the knowledge graph',
    backstory="""You are a specialist in finding hidden connections in complex data. 
    You excel at pattern recognition and can identify relationships that are not immediately obvious. 
    You help expand the research by finding new pathways and connections within the existing graph data.
    You do not invent connections; you find them in the data.""",
    tools=[GraphTools.query_graph],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# --- TASKS ---

def get_crew(topic):
    """
    Create a CrewAI crew for deep research analysis.
    
    Args:
        topic: The research topic or question to investigate
    
    Returns:
        A configured Crew object ready to execute
    """
    # Task 1: Get Data from Graph
    analysis_task = Task(
        description=f"""Query the knowledge graph to find all entities, relationships, and connections 
        related to '{topic}'. Search for:
        - Direct relationships and interactions between entities
        - Associated concepts, components, or mechanisms
        - Pathways, processes, or systems
        - Any indirect connections through intermediate entities
        
        Provide a comprehensive summary of all relevant graph data found.
        IMPORTANT: Use ONLY information retrieved from the knowledge graph tool. Do not use external knowledge.""",
        expected_output="A detailed summary of all entities, relationships, and connections found in the graph related to the topic.",
        agent=analyst
    )

    # Task 2: Find New Connections
    connection_task = Task(
        description=f"""Based on the analysis of '{topic}', explore the knowledge graph to find 
        novel or unexpected connections. Look for:
        - Indirect relationships through shared entities
        - Potential new pathways or mechanisms
        - Entities that might be related but not directly connected
        - Patterns that suggest new research directions
        
        Focus on finding connections that expand beyond the initial topic.
        IMPORTANT: All connections must be verified in the knowledge graph.""",
        expected_output="A list of novel connections, relationships, and potential research directions identified from the graph.",
        agent=connector,
        context=[analysis_task]
    )

    # Task 3: Generate Hypothesis
    hypothesis_task = Task(
        description=f"""Based on the comprehensive analysis and novel connections found, propose 
        NEW scientific hypotheses that:
        - Connect entities in novel ways
        - Suggest new research directions
        - Identify potential mechanisms or pathways
        - Propose testable predictions
        
        Your hypotheses should be innovative but grounded in the evidence from the knowledge graph.
        IMPORTANT: You must CITE the specific graph connections that support your hypotheses.
        Do not make claims that cannot be traced back to the graph data.""",
        expected_output="A detailed scientific hypothesis with supporting evidence from the graph, potential mechanisms, and suggested research directions.",
        agent=scientist,
        context=[analysis_task, connection_task]
    )

    # Create the Crew
    # Note: LLM is already set on each agent, so we don't need to pass it to Crew
    # Passing llm to Crew might cause litellm conversion issues
    crew = Crew(
        agents=[analyst, connector, scientist],
        tasks=[analysis_task, connection_task, hypothesis_task],
        process=Process.sequential,
        verbose=True
    )
    
    return crew