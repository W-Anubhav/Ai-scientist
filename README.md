# 🧬 AI Research Knowledge Graph System

A comprehensive application that transforms research papers into interactive knowledge graphs, enabling researchers to explore, query, and discover new connections using AI-powered analysis.

## ✨ Features

- **📤 PDF Upload**: Upload multiple research paper PDFs directly through the web interface
- **🔍 Natural Language Querying**: Ask questions in plain English to explore your knowledge graph
- **📊 Interactive Visualization**: Visualize your knowledge graph with interactive network diagrams
- **🤖 AI Scientist Crew**: Deploy a team of AI agents to find novel connections and generate hypotheses
- **💾 Neo4j Storage**: Robust graph database storage for your knowledge graph
- **🎨 Beautiful UI**: Modern, interactive interface built with Streamlit

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Neo4j Database (running locally or remotely)
- Google Gemini API Key

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd baby1
   ```

2. **Create a virtual environment (if not already created)**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   
   Create a `.env` file in the project root with the following:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your_neo4j_password_here
   ```

6. **Start Neo4j**
   
   Make sure Neo4j is running. You can download it from [neo4j.com](https://neo4j.com/download/) or use Neo4j Desktop.

7. **Run the application**
   ```bash
   streamlit run app.py
   ```

   The application will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Upload & Process PDFs

1. Navigate to the **"Upload & Process"** tab
2. Click "Choose PDF files" and select one or more research paper PDFs
3. Click **"🚀 Process PDFs & Extract Knowledge"**
4. Wait for processing (this may take a few minutes depending on PDF size)
5. The extracted knowledge triples will be automatically saved to Neo4j

### 2. Query Your Knowledge Graph

1. Go to the **"Query Graph"** tab
2. Enter a natural language question, such as:
   - "What are all entities related to Alzheimer's disease?"
   - "List all proteins and their relationships"
   - "What mechanisms are associated with neuroinflammation?"
3. Click **"🔍 Search"** to get answers from your knowledge graph

### 3. Visualize the Graph

1. Open the **"Visualize"** tab
2. Choose visualization options:
   - Number of relationships to show
   - Visualization type (Full Graph, Entity Connections, or Random Sample)
3. Click **"🔄 Generate Visualization"** to create an interactive graph

### 4. AI Scientist Crew

1. Navigate to the **"AI Scientists"** tab
2. Enter a research topic or question
3. Click **"🚀 Launch AI Crew"** to deploy:
   - **Graph Analyst**: Queries and analyzes the knowledge graph
   - **Research Connector**: Finds novel connections
   - **Lead Scientist**: Generates innovative hypotheses
4. Review the generated analysis and hypotheses

## 🏗️ Architecture

### Components

- **`app.py`**: Main Streamlit application with UI
- **`extract_graph.py`**: PDF processing and knowledge extraction using Gemini AI
- **`populate_Graph.py`**: Neo4j database population
- **`tools.py`**: LangChain tools for graph querying
- **`agents.py`**: CrewAI agent definitions
- **`graph_utils.py`**: Graph visualization and utility functions

### Technology Stack

- **Frontend**: Streamlit
- **LLM**: Google Gemini (gemini-2.0-flash-exp)
- **Graph Database**: Neo4j
- **AI Agents**: CrewAI
- **Graph Processing**: LangChain
- **Visualization**: Pyvis, NetworkX
- **PDF Processing**: pdfplumber

## 🔧 Configuration

### Gemini API

The application uses Google Gemini API for all LLM operations. Make sure you have:
- A valid Gemini API key
- Sufficient API quota
- The key set in your `.env` file as `GOOGLE_API_KEY`

### Neo4j Configuration

Update your Neo4j connection details in `.env`:
- `NEO4J_URI`: Connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USERNAME`: Database username (default: `neo4j`)
- `NEO4J_PASSWORD`: Your Neo4j password

## 📝 Notes

- **Rate Limiting**: The application includes rate limiting and retry logic to handle API limits gracefully
- **Processing Time**: Large PDFs may take several minutes to process
- **Graph Size**: Very large knowledge graphs may take time to visualize
- **Storage**: Make sure you have sufficient disk space for temporary files

## 🐛 Troubleshooting

### Neo4j Connection Issues
- Ensure Neo4j is running
- Check your connection credentials in `.env`
- Verify the Neo4j URI is correct

### API Errors
- Check your Gemini API key is valid
- Ensure you have sufficient API quota
- Wait a few minutes if you hit rate limits

### PDF Processing Errors
- Ensure PDFs are not corrupted
- Check that PDFs contain extractable text (not just images)
- Try processing one PDF at a time for debugging

## 🎯 Use Cases

- **Research Literature Review**: Build knowledge graphs from multiple research papers
- **Hypothesis Generation**: Use AI agents to discover new research directions
- **Concept Exploration**: Query and visualize relationships between concepts
- **Research Presentation**: Visualize knowledge graphs for presentations

## 📄 License

This project is for research and educational purposes.

## 🚀 Deployment

### Deploying to Streamlit Cloud

1. **Push your code to GitHub**
   - Ensure your repository is public or you have permissions to deploy private repos.
   - Make sure `requirements.txt` is in the root directory.

2. **Sign in to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.

3. **Deploy the App**
   - Click "New app".
   - Select your repository, branch (usually `main`), and main file path (`app.py`).
   - Click "Deploy!".

4. **Configure Secrets**
   - Once the app is deployed (it might fail initially due to missing secrets), go to the app dashboard.
   - Click on "Settings" -> "Secrets".
   - Add your secrets in the TOML format:

   ```toml
   GOOGLE_API_KEY = "your_gemini_api_key_here"
   NEO4J_URI = "bolt://your-neo4j-instance-url:7687"
   NEO4J_USERNAME = "neo4j"
   NEO4J_PASSWORD = "your_neo4j_password"
   ```

   > **Note**: For Neo4j, you'll need a cloud-hosted instance (like Neo4j AuraDB) since `localhost` won't work on Streamlit Cloud.

5. **Reboot the App**
   - After saving secrets, reboot the app if it doesn't restart automatically.

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the application!

---

**Built with ❤️ for researchers and scientists**






