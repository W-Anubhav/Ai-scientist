# Fixes for Query and CrewAI Issues

## ✅ Issue 1: Graph Query Always Says "I Don't Know"

**Problem**: Graph queries always return "I don't know" answers

**Root Causes**:
1. Graph might be empty (no data uploaded)
2. GraphCypherQAChain might not be configured optimally
3. Need better error handling and user feedback

**Solutions Applied**:
1. ✅ Added graph data check before querying
2. ✅ Improved error messages when graph is empty
3. ✅ Better handling of "I don't know" responses
4. ✅ Show graph statistics to user
5. ✅ Provide helpful tips when no results found
6. ✅ Display generated Cypher queries for debugging

**Files Modified**:
- `tools.py`: Added graph data validation and better response handling
- `app.py`: Added graph stats check and improved user feedback

## ✅ Issue 2: CrewAI Litellm Error

**Problem**: `litellm.BadRequestError: LLM Provider NOT provided. You passed model=models/gemini-flash-latest`

**Root Cause**: CrewAI was trying to use litellm with wrong model format. Litellm was getting "models/gemini-flash-latest" instead of "gemini/gemini-flash-latest"

**Solution Applied**:
1. ✅ Changed to use CrewAI's `LLM` class with correct litellm format
2. ✅ Model format: `"gemini/gemini-flash-latest"` (provider/model format)
3. ✅ Removed LLM from Crew initialization (already set on agents)
4. ✅ Added fallback to LangChain LLM if CrewAI LLM fails

**Files Modified**:
- `agents.py`: Updated to use CrewAI's LLM class with correct format

## Testing Checklist:

- [ ] Upload PDFs and process them
- [ ] Verify graph has data (check sidebar stats)
- [ ] Test graph querying with specific questions
- [ ] Test AI Crew launch
- [ ] Verify both work without errors

## Important Notes:

1. **Graph Must Have Data**: Queries will fail if graph is empty. Always upload and process PDFs first.

2. **Model Format**: 
   - For LangChain: `"gemini-flash-latest"` (no prefix)
   - For CrewAI/Litellm: `"gemini/gemini-flash-latest"` (provider/model format)

3. **Better Error Messages**: Users now get helpful guidance when queries fail

## If Issues Persist:

1. **Graph Query Issues**:
   - Check if graph has data (sidebar shows node/relationship counts)
   - Try asking about specific entities from your uploaded papers
   - Check the generated Cypher query in the expander

2. **CrewAI Issues**:
   - Make sure `litellm` is installed: `pip install litellm`
   - Check that `GOOGLE_API_KEY` is set correctly
   - Try restarting the application




