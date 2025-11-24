import os
import json
import glob
import time
import pdfplumber
from typing import List
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# 1. Load Secrets
# ... inside extract_graph.py ...
load_dotenv()

# ADD THESE LINES TO DEBUG:
key = os.getenv("GOOGLE_API_KEY")
print(f"DEBUG: My Key starts with: {key[:5]}... and ends with: ...{key[-5:]}")

# --- CONFIGURATION ---
PDF_FOLDER = "pdfs"       # Folder containing your PDF files
OUTPUT_FILE = "triples.json" # Final output file
CHUNK_SIZE = 15000         # Characters per chunk (reduced to avoid context limits) to leverage Gemini's context)
# ---------------------

# 2. Define the Strict Schema (Domain Agnostic)
class KnowledgeTriple(BaseModel):
    head: str = Field(description="The subject entity")
    relation: str = Field(description="The relationship connection (e.g., 'activates', 'causes', 'is_a')")
    tail: str = Field(description="The object entity")

class KnowledgeGraph(BaseModel):
    triples: List[KnowledgeTriple] = Field(description="List of knowledge triples extracted from the text")

# Initialize Gemini Models with retry configuration
# Model 1: For extraction (Structured Output)
llm_extraction = ChatGoogleGenerativeAI(
    model="gemini-flash-latest", 
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_retries=5,
    request_timeout=120
)

# Model 2: For domain detection (Simple Text Output)
llm_general = ChatGoogleGenerativeAI(
    model="gemini-flash-latest", 
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_retries=5,
    request_timeout=120
)

# 3. Helper Functions
def read_pdf(file_path_or_bytes):
    """Reads all text from a PDF file or bytes object using multiple methods."""
    text = ""
    
    # Method 1: Try pdfplumber (best for layout)
    try:
        if isinstance(file_path_or_bytes, bytes):
            import io
            with pdfplumber.open(io.BytesIO(file_path_or_bytes)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        else:
            with pdfplumber.open(file_path_or_bytes) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")

    # Method 2: Fallback to pypdf (more robust for some encodings)
    if not text or len(text.strip()) < 100:
        try:
            print("🔄 Falling back to pypdf extraction...")
            import pypdf
            import io
            
            if isinstance(file_path_or_bytes, bytes):
                reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
            else:
                reader = pypdf.PdfReader(file_path_or_bytes)
                
            pypdf_text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pypdf_text += extracted + "\n"
            
            if len(pypdf_text) > len(text):
                text = pypdf_text
                print("✅ pypdf extraction successful")
        except Exception as e:
            print(f"⚠️ pypdf failed: {e}")
            
    return text

def process_pdf_file(file_path_or_bytes, filename: str = None, progress_callback=None):
    """
    Process a single PDF file and extract triples.
    
    Args:
        file_path_or_bytes: Either a file path (str) or bytes object
        filename: Optional filename for metadata
        progress_callback: Optional callback function for progress updates
    
    Returns:
        List of extracted triples
    """
    all_triples = []
    
    try:
        # Read PDF
        raw_text = read_pdf(file_path_or_bytes)
        if not raw_text or len(raw_text.strip()) < 100:
            msg = f"⚠️ Warning: Empty or very short text found in {filename or 'file'}. This might be a scanned PDF (image-only)."
            if progress_callback:
                progress_callback(msg)
            print(msg)
            return []
        
        if progress_callback:
            progress_callback(f"📄 Processing {filename or 'file'}...")
        
        # Detect Domain
        current_domain = detect_domain(raw_text)
        if progress_callback:
            progress_callback(f"🧠 Detected Domain: {current_domain}")
        
        # Chunking
        chunks = [raw_text[j:j+CHUNK_SIZE] for j in range(0, len(raw_text), CHUNK_SIZE)]
        if progress_callback:
            progress_callback(f"✂️ Split into {len(chunks)} chunks. Extracting triples...")
        
        # Extract from each chunk
        chunks_with_triples = 0
        for k, chunk in enumerate(chunks):
            try:
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                    
                response = extract_triples(chunk, domain=current_domain)
                if response and response.triples and len(response.triples) > 0:
                    chunks_with_triples += 1
                    for t in response.triples:
                        triple_dict = t.dict()
                        triple_dict['source'] = filename or 'uploaded_file'
                        all_triples.append(triple_dict)
                elif progress_callback and k < 3:  # Show first few empty chunks
                    progress_callback(f"   ⚠️ Chunk {k+1}: No triples found (may be normal)")
                
                time.sleep(1.5)  # Rate limiting - reduced delay
                
                if progress_callback and (k + 1) % 5 == 0:
                    progress_callback(f"   Processed {k+1}/{len(chunks)} chunks ({chunks_with_triples} with triples)...")
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(f"   ❌ Error on chunk {k+1}: {str(e)[:100]}")
        
        if progress_callback:
            progress_callback(f"✅ Extracted {len(all_triples)} triples from {filename or 'file'}.")
        
        return all_triples
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Failed to process file: {e}")
        return []

def detect_domain(preview_text):
    """Asks Gemini to guess the domain from the first 1000 chars."""
    max_retries = 3
    base_delay = 3
    
    for attempt in range(max_retries):
        try:
            prompt = f"""
            Read the following text and identify the specific scientific domain or field of study.
            Return ONLY the domain name (e.g., "Molecular Biology", "Roman History", "Contract Law").
            
            TEXT PREVIEW:
            {preview_text[:1000]}...
            """
            response = llm_general.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            error_str = str(e).lower()
            if ("resourceexhausted" in error_str or "429" in error_str or "quota" in error_str) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"   ⏳ Rate limit hit, waiting {delay} seconds before retry...")
                time.sleep(delay)
            else:
                print(f"   ⚠️ Error detecting domain: {e}")
                return "Unknown Domain"  # Fallback

def extract_triples(text_chunk, domain):
    """Extracts triples using the specific domain context."""
    import json
    import re
    
    max_retries = 3
    base_delay = 5
    
    # Ensure text chunk is not empty
    if not text_chunk or len(text_chunk.strip()) < 50:
        return KnowledgeGraph(triples=[])
    
    for attempt in range(max_retries):
        try:
            # Use JSON extraction directly (more reliable than structured output)
            json_prompt = f"""You are an expert knowledge extraction analyst specializing in {domain}. 

Your task is to EXHAUSTIVELY extract knowledge triples from the following text. 
Do not summarize. Extract every single meaningful relationship found in the text.
Each triple should follow the format:
(Subject/Head Entity) -> (Relationship/Relation) -> (Object/Tail Entity)

Examples (domain-agnostic):
- "Concept A" -> "causes" -> "Effect B"
- "Entity X" -> "interacts_with" -> "Entity Y"
- "Component ABC" -> "regulates" -> "Process XYZ"
- "Theory 1" -> "contradicts" -> "Theory 2"
- "Method A" -> "improves" -> "Outcome B"

Text to analyze:
{text_chunk[:25000]}

IMPORTANT: Return ONLY a valid JSON array. No explanations, no markdown, just the JSON array.

Format:
[
  {{"head": "entity name", "relation": "relationship type", "tail": "entity name"}},
  {{"head": "entity name", "relation": "relationship type", "tail": "entity name"}}
]

Extract as many meaningful triples as possible (aim for 20-50+ per chunk if content allows). Focus on:
- Entities (concepts, objects, processes, theories, methods, components relevant to {domain})
- Relationships (causes, activates, inhibits, interacts_with, regulates, associated_with, improves, contradicts, supports, etc.)
- Clear factual statements and relationships
- Be specific with entity names (e.g., use "Alzheimer's disease" instead of "the disease")

Return the JSON array now:"""
            
            response = llm_general.invoke(json_prompt)
            
            # Extract JSON from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Clean the content - remove markdown code blocks if present
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            # Remove any leading/trailing text that isn't part of the JSON array
            content = content.strip()
            
            # Try to find JSON array with more robust regex
            # Matches [ ... ] including nested braces if simple, but mainly looks for outer brackets
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
            else:
                # Fallback: try to find just the array brackets if the content is just the array
                if content.startswith('[') and content.endswith(']'):
                    json_str = content
                else:
                    json_str = None

            if json_str:
                try:
                    # Fix common JSON errors from LLMs (like trailing commas)
                    json_str = re.sub(r',\s*\]', ']', json_str)
                    json_str = re.sub(r',\s*\}', '}', json_str)
                    
                    triples_data = json.loads(json_str)
                    
                    if isinstance(triples_data, list) and len(triples_data) > 0:
                        # Convert to KnowledgeGraph format
                        triples = []
                        for t in triples_data:
                            if isinstance(t, dict):
                                head = str(t.get('head', '')).strip()
                                relation = str(t.get('relation', '')).strip()
                                tail = str(t.get('tail', '')).strip()
                                
                                # Only add if all fields are non-empty
                                if head and relation and tail and len(head) > 0 and len(tail) > 0:
                                    triples.append(KnowledgeTriple(
                                        head=head,
                                        relation=relation,
                                        tail=tail
                                    ))
                        
                        if triples:
                            return KnowledgeGraph(triples=triples)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    # Try to extract triples from text if JSON parsing fails
                    pass
            
            # If JSON extraction failed, try a simpler approach
            if attempt == max_retries - 1:
                # Last attempt: try to extract at least some triples
                simple_prompt = f"""Extract 3-5 key knowledge triples from this {domain} text in JSON format:

{text_chunk[:2000]}

Return JSON: [{{"head": "...", "relation": "...", "tail": "..."}}]"""
                
                try:
                    simple_response = llm_general.invoke(simple_prompt)
                    simple_content = simple_response.content if hasattr(simple_response, 'content') else str(simple_response)
                    simple_json = re.search(r'\[.*?\]', simple_content, re.DOTALL)
                    if simple_json:
                        triples_data = json.loads(simple_json.group())
                        if isinstance(triples_data, list):
                            triples = []
                            for t in triples_data:
                                if isinstance(t, dict) and t.get('head') and t.get('relation') and t.get('tail'):
                                    triples.append(KnowledgeTriple(
                                        head=str(t['head']).strip(),
                                        relation=str(t['relation']).strip(),
                                        tail=str(t['tail']).strip()
                                    ))
                            if triples:
                                return KnowledgeGraph(triples=triples)
                except:
                    pass
            
            # If still no triples, return empty but don't fail
            return KnowledgeGraph(triples=[])
            
        except Exception as e:
            error_str = str(e).lower()
            if ("resourceexhausted" in error_str or "429" in error_str or "quota" in error_str) and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            elif attempt < max_retries - 1:
                time.sleep(2)  # Brief delay before retry
            else:
                # Return empty on final failure
                return KnowledgeGraph(triples=[])
    
    return KnowledgeGraph(triples=[])

# 4. Main Execution Loop
if __name__ == "__main__":
    all_master_triples = []
    
    # Find all PDF files in the folder
    pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in '{PDF_FOLDER}' folder!")
    else:
        print(f"🔎 Found {len(pdf_files)} PDFs. Starting processing...\n")

        for i, pdf_file in enumerate(pdf_files):
            filename = os.path.basename(pdf_file)
            file_triples = process_pdf_file(pdf_file, filename=filename, progress_callback=print)
            all_master_triples.extend(file_triples)

        # 5. Save Final Result
        print(f"💾 Saving total {len(all_master_triples)} triples to '{OUTPUT_FILE}'...")
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_master_triples, f, indent=2)
        
        print("🎉 Done! You can now run 'python populate_graph.py'")