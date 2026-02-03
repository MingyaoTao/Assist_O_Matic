import ollama
import datetime
import re
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

# --- TOOL 1: THE CLOCK ---
def get_current_time_str():
    return datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

# --- TOOL 2: THE BROWSER (Link Fetcher) ---
def fetch_url_content(url):
    try:
        print(f"🌐 Fetching link: {url}...")
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Kill script and style elements (CSS/JS)
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text and clean it up
        text = soup.get_text()
        clean_text = " ".join(text.split())[:8000] # Limit to 8k characters to save RAM
        return f"\n[START WEBPAGE CONTENT: {url}]\n{clean_text}\n[END WEBPAGE CONTENT]\n"
    except Exception as e:
        return f"[Error fetching link: {e}]"

# --- TOOL 3: THE READER (PDF Extractor) ---
def extract_pdf_text(file_path):
    try:
        print(f"📄 Reading PDF: {file_path}...")
        doc = fitz.open(file_path)
        text = ""
        # Read first 10 pages only (to save context window)
        for page in doc[:10]: 
            text += page.get_text()
        return f"\n[START PDF CONTENT: {file_path}]\n{text[:10000]}\n[END PDF CONTENT]\n"
    except Exception as e:
        return f"[Error reading PDF: {e}]"
    
# --- NEW TOOL: THE RECORDER (Logger) ---
def save_chat_log(history):
    # 1. Generate a filename with a timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"chat_log_{timestamp}.txt"
    
    print(f"\n💾 Saving full chat log to '{filename}'...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== ASSIST-O-MATIC SESSION LOG: {timestamp} ===\n\n")
        
        for message in history:
            role = message['role'].upper()
            content = message['content']
            
            # We create a nice divider for each message
            f.write(f"[{role} MESSAGE]\n")
            f.write("-" * 50 + "\n")
            f.write(content + "\n")
            f.write("-" * 50 + "\n\n")
            
    print("✅ Log saved successfully.")

# --- MAIN LOOP ---
def chat_with_secretary():
    print(f"🤖 Secretary Online. (Time: {get_current_time_str()})")
    
    # Context buffer (so it remembers the previous question)
    conversation_history = []

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]: 
            save_chat_log(conversation_history)
            break

        # 1. PRE-PROCESS: Check for PDFs (File paths)
        # (Simple logic: if input ends in .pdf, treat it as a file)
        context_data = ""
        if user_input.strip().endswith(".pdf"):
            context_data += extract_pdf_text(user_input.strip())
            # We don't replace the input, we just append the content to the context

        # 2. PRE-PROCESS: Check for Links (http/https)
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', user_input)
        for url in urls:
            context_data += fetch_url_content(url)

        # 3. BUILD PROMPT
        # We construct the "System Message" fresh every time to update the clock
        system_msg = f"""
        You are a smart personal secretary.
        CURRENT TIME: {get_current_time_str()}
        
        INSTRUCTIONS:
        - If the user asks about a link or PDF, the content is provided below.
        - Be concise.
        """

        # Combine User Input + Any Scraped Data
        full_prompt = f"{user_input}\n\n{context_data}"

        # 4. SEND TO OLLAMA
        print("Thinking...")
        
        # We append to history for conversational flow
        conversation_history.append({'role': 'user', 'content': full_prompt})
        
        # Note: If history gets too long, M2 Air might slow down. 
        # In V3 we will trim this list.
        response = ollama.chat(
            model='deepseek-r1:8b', # Or 'llama3'
            messages=[{'role': 'system', 'content': system_msg}] + conversation_history
        )

        reply = response['message']['content']
        print(f"Secretary: {reply}")
        
        # Add reply to history
        conversation_history.append({'role': 'assistant', 'content': reply})

if __name__ == "__main__":
    chat_with_secretary()