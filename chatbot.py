import requests
import json
import os
from datetime import datetime
import re
from typing import List, Dict, Optional

class WikiChatbot:
    def __init__(self, wiki_data_file: str = "wiki_data.json"):
        self.wiki_data_file = wiki_data_file
        self.wiki_data = []
        self.load_wiki_data()
        
    def load_wiki_data(self):
        """Load scraped wiki data"""
        if os.path.exists(self.wiki_data_file):
            try:
                with open(self.wiki_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.wiki_data = data.get('pages', [])
                print(f"✅ Loaded {len(self.wiki_data)} wiki pages")
            except Exception as e:
                print(f"❌ Error loading wiki data: {e}")
                self.wiki_data = []
        else:
            print(f"❌ Wiki data file {self.wiki_data_file} not found")
            self.wiki_data = []
    
    def textOne(self, prompt: str) -> str:
        """Your AI function"""
        try:
            baseurl = "https://tools.originality.ai/tool-ai-prompt-generator/backend/generate.php"
            json_data = {"prompt": prompt}
            response = requests.post(baseurl, json=json_data, timeout=30)
            return response.json()["output"]
        except Exception as e:
            return f"❌ AI Error: {str(e)}"
    
    def search_wiki(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search through wiki pages"""
        if not self.wiki_data:
            return []
        
        query_lower = query.lower()
        results = []
        
        for page in self.wiki_data:
            score = 0
            title = page.get('title', '').lower()
            content = page.get('content', '').lower()
            categories = ' '.join(page.get('categories', [])).lower()
            
            # Scoring system
            if query_lower in title:
                score += 10
            if query_lower in categories:
                score += 5
            if query_lower in content:
                score += 1
            
            # Check for partial matches
            for word in query_lower.split():
                if word in title:
                    score += 3
                if word in content:
                    score += 0.5
            
            if score > 0:
                results.append({
                    'page': page,
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['page'] for r in results[:max_results]]
    
    def format_search_results(self, pages: List[Dict]) -> str:
        """Format search results for context"""
        if not pages:
            return "No relevant wiki pages found."
        
        context = "Relevant FOSSCELL Wiki pages:\n\n"
        for i, page in enumerate(pages, 1):
            title = page.get('title', 'Unknown')
            content = page.get('content', '')[:300]  # First 300 chars
            url = page.get('url', '')
            
            context += f"{i}. **{title}**\n"
            context += f"   Content: {content}...\n"
            context += f"   URL: {url}\n\n"
        
        return context
    
    def create_context_prompt(self, user_question: str, wiki_context: str) -> str:
        """Create a comprehensive prompt with wiki context"""
        prompt = f"""You are a helpful AI assistant for FOSSCELL (Free and Open Source Software Cell). 

FOSSCELL Wiki Context:
{wiki_context}

User Question: {user_question}

Instructions:
- Answer the user's question using the FOSSCELL wiki information provided above when relevant
- If the wiki contains relevant information, reference it in your answer
- If the question is not covered in the wiki, provide a helpful general answer
- Be friendly and informative
- If you mention wiki pages, include their titles
- Keep answers concise but comprehensive

Answer:"""
        
        return prompt
    
    def chat(self, user_input: str) -> str:
        """Main chat function"""
        if not user_input.strip():
            return "Please ask me something!"
        
        # Search for relevant wiki pages
        relevant_pages = self.search_wiki(user_input)
        wiki_context = self.format_search_results(relevant_pages)
        
        # Create comprehensive prompt
        full_prompt = self.create_context_prompt(user_input, wiki_context)
        
        # Get AI response
        ai_response = self.textOne(full_prompt)
        
        return ai_response
    
    def run_interactive(self):
        """Run interactive chatbot"""
        print("🤖 FOSSCELL Wiki AI Chatbot")
        print("=" * 40)
        print(f"📚 Loaded {len(self.wiki_data)} wiki pages")
        print("💬 Ask me anything about FOSSCELL or general topics!")
        print("🔍 I'll search the wiki for relevant information")
        print("Type 'quit', 'exit', or 'bye' to stop")
        print("-" * 40)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                    print("👋 Goodbye! Thanks for chatting!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 AI: Thinking...", end="", flush=True)
                response = self.chat(user_input)
                print(f"\r🤖 AI: {response}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye! Thanks for chatting!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

class WikiChatbotWeb:
    """Simple web interface for the chatbot"""
    def __init__(self, chatbot: WikiChatbot, port: int = 8000):
        self.chatbot = chatbot
        self.port = port
    
    def create_web_interface(self):
        """Create a simple web interface"""
        wiki_count = len(self.chatbot.wiki_data)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FOSSCELL Wiki AI Chatbot</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .chat-container {{ border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 10px; margin: 10px 0; }}
        .message {{ margin: 10px 0; }}
        .user {{ color: #0066cc; font-weight: bold; }}
        .ai {{ color: #cc6600; }}
        input[type="text"] {{ width: 70%; padding: 10px; }}
        button {{ padding: 10px 20px; background: #0066cc; color: white; border: none; cursor: pointer; }}
        .stats {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🤖 FOSSCELL Wiki AI Chatbot</h1>
    <div class="stats">
        📚 Loaded {wiki_count} wiki pages | 🔍 AI-powered search & answers
    </div>
    <div id="chat" class="chat-container"></div>
    <div>
        <input type="text" id="userInput" placeholder="Ask me anything about FOSSCELL..." onkeypress="handleKeyPress(event)">
        <button onclick="sendMessage()">Send</button>
    </div>
    
    <script>
        async function sendMessage() {{
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage('👤 You: ' + message, 'user');
            input.value = '';
            
            addMessage('🤖 AI: Thinking...', 'ai');
            
            try {{
                const response = await fetch('/chat', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message: message}})
                }});
                const data = await response.json();
                
                // Replace the "thinking" message
                const chatDiv = document.getElementById('chat');
                chatDiv.removeChild(chatDiv.lastChild);
                addMessage('🤖 AI: ' + data.response, 'ai');
            }} catch (error) {{
                addMessage('🤖 AI: Sorry, there was an error.', 'ai');
            }}
        }}
        
        function addMessage(text, className) {{
            const chatDiv = document.getElementById('chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + className;
            messageDiv.innerHTML = text.replace(/\\n/g, '<br>');
            chatDiv.appendChild(messageDiv);
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }}
        
        function handleKeyPress(event) {{
            if (event.key === 'Enter') {{
                sendMessage();
            }}
        }}
        
        // Welcome message
        addMessage('👋 Welcome! Ask me anything about FOSSCELL or general topics. I will search through the wiki for relevant information.', 'ai');
    </script>
</body>
</html>
        """
        return html
    
    def run_web_server(self):
        """Run simple web server"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse
            
            class ChatHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        html = self.server.chatbot_web.create_web_interface()
                        self.wfile.write(html.encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def do_POST(self):
                    if self.path == '/chat':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode())
                        
                        response = self.server.chatbot_web.chatbot.chat(data['message'])
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'response': response}).encode())
            
            server = HTTPServer(('localhost', self.port), ChatHandler)
            server.chatbot_web = self
            
            print(f"🌐 Web chatbot running at http://localhost:{self.port}")
            print("📱 Open the URL in your browser")
            print("⏹️  Press Ctrl+C to stop")
            
            server.serve_forever()
            
        except ImportError:
            print("❌ Web server requires Python's built-in http.server module")
        except Exception as e:
            print(f"❌ Web server error: {e}")

def main():
    """Main function"""
    print("🚀 FOSSCELL Wiki AI Chatbot")
    print("Choose mode:")
    print("1. Interactive Terminal Chat")
    print("2. Web Interface")
    
    try:
        choice = input("Enter 1 or 2: ").strip()
        
        # Initialize chatbot
        chatbot = WikiChatbot()
        
        if choice == "1":
            chatbot.run_interactive()
        elif choice == "2":
            web_chatbot = WikiChatbotWeb(chatbot)
            web_chatbot.run_web_server()
        else:
            print("Invalid choice. Running interactive mode...")
            chatbot.run_interactive()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()