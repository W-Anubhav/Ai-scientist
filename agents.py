import os
from crewai import Agent, Task, Crew, Process, LLM as CrewLLM
from tools import GraphTools 
from dotenv import load_dotenv

load_dotenv()

# Define LLMs (Global)
# Check for API key
if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️ WARNING: GOOGLE_API_KEY not found in environment variables!")

llm_fast = CrewLLM(model="gemini/gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
llm_smart = CrewLLM(model="gemini/gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"), temperature=0.7)

def get_crew(topic, domain="Scientific Research"):
    """
    Creates a dynamic crew that adapts its persona to the specific domain.
    Args:
        topic: The specific subject (e.g., "Adversarial Attacks on GNNs")
        domain: The broader field (e.g., "Computer Science", "Sociology", "Biology")
    """

    # --- 1. DYNAMIC AGENTS (Defined inside to use 'domain') ---

    # Agent 1: The Cartographer (Maps the territory)
    analyst = Agent(
        role=f'Senior {domain} Analyst',
        goal=f'Deconstruct the topic "{topic}" into its fundamental structural components and mechanisms based strictly on the Knowledge Graph.',
        backstory=f"""You are an expert taxonomist and analyst in the field of {domain}. 
        Your strength is breaking down complex systems into their atomic parts.
        You do not just summarize; you map the architecture of concepts.
        You strictly rely on the provided Knowledge Graph.""",
        tools=[GraphTools.query_graph],
        llm=llm_fast,
        verbose=True
    )

    # Agent 2: The Paradox Hunter (Finds the gaps)
    # This is the key "Agnostic" agent. It looks for logic failures, not specific tech bugs.
    conflict_hunter = Agent(
        role='Structural Paradox Detective',
        goal='Identify theoretical tensions, trade-offs, or contradictions between the mapped concepts.',
        backstory=f"""You are a critical thinker who looks for "Logical Friction" in {domain}.
        You look for patterns like:
        1. Resource Contradictions (Mechanism A requires X, but Mechanism B destroys X).
        2. Scale Mismatches (Concept A is micro-level, Concept B is macro-level, and they don't align).
        3. Objectives Conflict (Goal A opposes Goal B).
        You ignore the happy path and hunt for the problems.""",
        tools=[GraphTools.query_graph],
        llm=llm_smart,
        verbose=True
    )

    # Agent 3: The Synthesizer (The Scientist)
    scientist = Agent(
        role=f'Lead {domain} Researcher',
        goal='Propose a novel theoretical mechanism or framework that resolves the identified paradox.',
        backstory=f"""You are a visionary in {domain}. You excel at "Dialectical Synthesis"—taking two opposing concepts (Thesis and Antithesis) found by the Detective and creating a new solution (Synthesis).
        Your hypotheses are always:
        1. Grounded in the graph data.
        2. Architecturally precise.
        3. Aimed at solving the specific friction identified.""",
        llm=llm_smart,
        verbose=True
    )

    # Agent 4: The Gatekeeper (The Reviewer)
    reviewer = Agent(
        role=f'Distinguished Reviewer (Top-Tier {domain} Journal)',
        goal='Rigorously critique the hypothesis for novelty, feasibility, and theoretical soundness.',
        backstory=f"""You are a notoriously difficult reviewer for the top journals in {domain}.
        You reject ideas that are:
        - Derivative (just mixing two old things).
        - Vague (lacking specific mechanisms).
        - Illogical.
        You force the Scientist to be precise.""",
        llm=llm_smart,
        verbose=True
    )

    # --- 2. DYNAMIC TASKS (Using Abstract Logic) ---

    # Task 1: Mapping
    t1 = Task(
        description=f"""Query the graph for '{topic}'. 
        Deconstruct the topic into its core 'Mechanisms' or 'Components'.
        Output a structured list of:
        - Active Agents/Components (Who is acting?)
        - Rules/Processes (How do they act?)
        - Constraints (What limits them?)""",
        expected_output=f"A structural breakdown of the {domain} concepts related to {topic}.",
        agent=analyst
    )

    # Task 2: Friction Hunting
    t2 = Task(
        description=f"""Review the components from Task 1. 
        Identify a 'Systemic Tension'.
        Find two components or rules that work against each other.
        Ask: "Where does the system break or become inefficient?"
        Output the specific conflict clearly.""",
        expected_output="A defined structural paradox or trade-off between two entities.",
        agent=conflict_hunter,
        context=[t1]
    )

    # Task 3: Hypothesis Generation
    t3 = Task(
        description=f"""Propose a novel solution to the Tension found in Task 2.
        Don't just say 'combine them'. Propose a specific *mechanism* that bridges the gap.
        If this is CS, propose an Architecture.
        If this is Soc, propose a Theory.
        If this is Bio, propose a Pathway.
        Title it: 'The [Mechanism] Hypothesis'.""",
        expected_output="A detailed hypothesis with a proposed resolution mechanism.",
        agent=scientist,
        context=[t2]
    )

    # Task 4: Review
    t4 = Task(
        description=f"""Critique the hypothesis.
        If it fails your high standards for {domain} research, explain why.
        If it passes, refine the terminology to match the highest academic standards of the field.""",
        expected_output="A final critique or a polished, submission-ready hypothesis.",
        agent=reviewer,
        context=[t3]
    )

    # Task 5: The Pivot (Scientist fixes the flaws)
    t5 = Task(
        description=f"""
        You have received a brutal rejection from the Reviewer (Task 4). 
        Your 'Contextual Checksum' idea was rejected because:
        1. The 'Mean' aggregation is too lossy (it blurs meaning).
        2. It suffers from the 'Moving Target' problem.

        **YOUR GOAL:** Re-write the hypothesis to solve these specific problems.
        
        **New Constraints:**
        - Instead of predicting a 'Mean', use a **Contrastive Loss** (e.g., InfoNCE).
        - The [CLS] token should be trained to maximize similarity with the *original unmasked sentence embedding*, while pushing away negative samples.
        - Explicitly mention using a **Stop-Gradient** on the target encoder to fix the 'Moving Target' stability issue (Reference: BYOL or SimSiam).
        
        Title the new hypothesis: 'Contrastive Contextual Alignment (CCA)'.
        """,
        expected_output="A revised, mathematically sound hypothesis that addresses the Reviewer's critique.",
        agent=scientist, # The Scientist tries again
        context=[t3, t4] # Reads their old idea and the critique
    )

    # --- 3. CREATE CREW ---
    crew = Crew(
        agents=[analyst, conflict_hunter, scientist, reviewer],
        tasks=[t1, t2, t3, t4, t5], # Added the loop
        process=Process.sequential,
        verbose=True
    )
    
    return crew