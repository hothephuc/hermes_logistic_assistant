import google.generativeai as genai
import pandas as pd
from app.services.data_service import load_data, get_unique_values
from app.ai.predictor import predict_delay
from app.core.config import settings

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

def process_query(query: str, df: pd.DataFrame) -> str:
    """
    Process a natural language query using Gemini and return a response.
    """
    # List of models to try
    candidate_models = [
        'gemini-2.0-flash',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-flash-latest',
        'gemini-pro-latest',
        'gemini-1.5-flash',
    ]

    # Prepare context
    columns = ", ".join(df.columns)
    sample_data = df.head(3).to_string()
    
    prompt = f"""
    You are Hermes, a logistics assistant.
    You have access to a dataframe with columns: {columns}.
    Sample data:
    {sample_data}

    User Query: "{query}"

    Instructions:
    1. If the user asks for a prediction about next week's delay, reply with "PREDICT_DELAY".
    2. If the user asks a question that can be answered by filtering or aggregating the data, generate a PYTHON CODE SNIPPET to do it. 
       The dataframe is named 'df'. 
       The code should print the result. 
       Do NOT wrap in markdown blocks. Just the code.
       Example: print(df[df['delay_minutes'] > 0].count())
    3. If it's a general question or greeting, just answer politely.
    
    Response:
    """

    last_error = None
    
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text == "PREDICT_DELAY":
                return f"Predicted average delay for next week: {predict_delay(df)} minutes."
            
            # Check if it looks like code (simple heuristic)
            if "df" in text and ("print" in text or "=" in text):
                try:
                    # Capture stdout
                    import io
                    import sys
                    old_stdout = sys.stdout
                    new_stdout = io.StringIO()
                    sys.stdout = new_stdout
                    
                    local_vars = {'df': df, 'pd': pd}
                    exec(text, {}, local_vars)
                    
                    output = new_stdout.getvalue().strip()
                    sys.stdout = old_stdout
                    return output if output else "Executed query but got no output."
                except Exception as e:
                    sys.stdout = old_stdout
                    return f"Error executing query: {e}"
            
            return text

        except Exception as e:
            last_error = e
            print(f"Model {model_name} failed: {e}")
            continue

    # If all models fail
    available_models = []
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except:
        pass
        
    return f"All models failed. Last error: {last_error}. Available models: {available_models}"
