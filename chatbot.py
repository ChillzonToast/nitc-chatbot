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
    
    def generate_keywords(self, user_question: str) -> List[Dict]:
        """Use AI to generate weighted keywords from user's question"""
        keyword_prompt = f"""Extract keywords with importance weights from this question for searching a technical wiki database.

Question: {user_question}

Instructions:
- Extract 5-15 keywords with their importance weights (1-10, where 10 is most important)
- Include exact terms from the question with highest weights
- Format as: keyword:weight (one per line)
- No explanations, just keyword:weight pairs
- Only generate necessary keywords
- Don't assume keywords, just generate based on the question.
- Ignore common words like "the", "is", "in", "what", "how", "why", "an", "a", "and", "or", "but", "if", "then", "else", "there", "here", "now", "then", "there", "here", "now", etc.

Example format:
docker:10
container:9
deployment:2
devops:1

Keywords with weights:"""
        
        try:
            ai_response = self.textOne(keyword_prompt)
            weighted_keywords = []
            
            # Parse weighted keywords from AI response
            for line in ai_response.split('\n'):
                line = line.strip()
                if ':' in line and line:
                    try:
                        keyword, weight = line.split(':', 1)
                        keyword = keyword.strip().lower()
                        weight = float(weight.strip())
                        if len(keyword) > 1 and 1 <= weight <= 10:
                            weighted_keywords.append({
                                'keyword': keyword,
                                'weight': weight
                            })
                    except (ValueError, IndexError):
                        continue
            
            # Fallback: add original question words with high weight if no good keywords found
            if not weighted_keywords:
                for word in user_question.lower().split():
                    if len(word) > 2:
                        weighted_keywords.append({
                            'keyword': word,
                            'weight': 10.0
                        })
            
            # Sort by weight (highest first)
            weighted_keywords.sort(key=lambda x: x['weight'], reverse=True)
            
            print(f"🎯 AI weighted keywords: {weighted_keywords}")
            return weighted_keywords
            
        except Exception as e:
            print(f"❌ Error generating weighted keywords: {e}")
            # Fallback to simple extraction with high weights
            return [{'keyword': word.lower(), 'weight': 10.0} for word in user_question.split() if len(word) > 2]
    
    def calculate_match_score(self, page: Dict, weighted_keywords: List[Dict]) -> float:
        """Calculate match score using weighted keywords"""
        score = 0.0
        
        title = page.get('title', '').lower()
        content = page.get('content', '').lower()
        categories = ' '.join(page.get('categories', [])).lower()
        
        for kw_data in weighted_keywords:
            keyword = kw_data['keyword']
            weight = kw_data['weight']
            
            # Exact title match (highest priority)
            if keyword == title:
                score += 50.0 * weight
            elif keyword in title:
                score += 20.0 * weight
            
            # Exact matches in categories
            if keyword in categories:
                score += 15.0 * weight
            
            # Content matches
            content_matches = content.count(keyword)
            score += content_matches * 2.0 * weight
            
            # Word boundary matches in title (prevents partial word false positives)
            import re
            if re.search(r'\b' + re.escape(keyword) + r'\b', title):
                score += 25.0 * weight
            
            # Word boundary matches in content (first 200 words for performance)
            content_start = ' '.join(content.split()[:200])
            if re.search(r'\b' + re.escape(keyword) + r'\b', content_start):
                score += 5.0 * weight
            
            # Partial word matches (lower priority)
            for word in title.split():
                if keyword in word and len(keyword) > 3:
                    score += 3.0 * weight
        
        return score
    
    def get_best_matching_pages(self, user_question: str, top_n: int = 10) -> List[Dict]:
        """Get top N best matching pages using weighted AI keywords"""
        if not self.wiki_data:
            return []
        
        # Generate weighted keywords using AI
        weighted_keywords = self.generate_keywords(user_question)
        
        # Calculate scores for all pages
        page_scores = []
        for page in self.wiki_data:
            score = self.calculate_match_score(page, weighted_keywords)
            if score > 0:  # Only include pages with some relevance
                page_scores.append({
                    'page': page,
                    'score': score
                })
        
        # Sort by score and return top N
        page_scores.sort(key=lambda x: x['score'], reverse=True)
        top_pages = [item['page'] for item in page_scores[:top_n]]
        
        print(f"📊 Found {len(page_scores)} relevant pages, using top {len(top_pages)}")
        if top_pages:
            print(f"🔍 Top 5 pages: {', '.join([page['title'] for page in top_pages[:5]])}")
        
        return top_pages
    
    def format_context_pages(self, pages: List[Dict]) -> str:
        """Format selected pages as context"""
        if not pages:
            return "No relevant wiki pages found."
        
        context = "Relevant FOSSCELL Wiki Pages:\n\n"
        for i, page in enumerate(pages, 1):
            title = page.get('title', 'Unknown')
            content = page.get('content', '')
            categories = page.get('categories', [])
            url = page.get('url', '')
            
            context += f"=== Page {i}: {title} ===\n"
            if categories:
                context += f"Categories: {', '.join(categories)}\n"
            context += f"URL: {url}\n"
            context += f"Content: {content}\n\n"
        
        return context
    
    def create_context_prompt(self, user_question: str, wiki_context: str) -> str:
        """Create a comprehensive prompt with selected wiki context"""
        prompt = f"""You are a helpful AI assistant for FOSSCELL (Free and Open Source Software Cell). 

I have selected the most relevant pages from the FOSSCELL wiki database based on your question:

{wiki_context}

User Question: {user_question}

Instructions:
- Use the FOSSCELL wiki information above to answer the user's question
- Reference specific pages, tutorials, or resources when relevant
- If the question is not fully covered in the wiki, provide helpful general information
- Be friendly and informative
- Mention page titles when referencing specific information
- Keep answers comprehensive but well-organized

Answer:"""
        
        return prompt
    
    def chat(self, user_input: str) -> str:
        """Main chat function with AI keyword matching"""
        if not user_input.strip():
            return "Please ask me something!"
        
        print(f"🤔 Processing question: {user_input}")
        
        # Get best matching pages using weighted AI keywords
        best_pages = self.get_best_matching_pages(user_input)
        
        # Format context
        wiki_context = self.format_context_pages(best_pages)
        
        # Create comprehensive prompt
        full_prompt = self.create_context_prompt(user_input, wiki_context)
        
        print("🧠 Generating AI response...")
        
        # Get AI response
        ai_response = self.textOne(full_prompt)
        
        return ai_response
    
    def run_interactive(self):
        """Run interactive chatbot"""
        print("🤖 FOSSCELL Wiki AI Chatbot")
        print("=" * 40)
        print(f"📚 Loaded {len(self.wiki_data)} wiki pages")
        print("💬 Ask me anything about FOSSCELL or general topics!")
        print("🔍 I'll use AI to find the most relevant pages")
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
        📚 Loaded {wiki_count} wiki pages | 🔍 AI-powered smart search
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
        addMessage('👋 Welcome! Ask me anything about FOSSCELL or general topics. I have access to the complete wiki database.', 'ai');
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