import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from phi.agent import Agent
from phi.model.openai.chat import OpenAIChat
from phi.tools.yfinance import YFinanceTools
from phi.tools.duckduckgo import DuckDuckGo

# Load environment variables from .env file
load_dotenv()

# Set API keys
openai_api_key = os.getenv("OPENAI_API_KEY")

# If the OPENAI_API_KEY is not in the environment, set it directly
if not openai_api_key:
    # Replace this with your actual API key if not using .env
    openai_api_key = "your_openai_api_key_here"
    os.environ["OPENAI_API_KEY"] = openai_api_key

# Define the OpenAI model with API key (supports tool calling)
model = OpenAIChat(
    model="gpt-3.5-turbo-0125",  # This model supports tool calling
    api_key=openai_api_key  # Pass the API key directly to the model
)

# Web search agent
web_search_agent = Agent(
    name="Web Search Agent",
    role="Search the web for the information",
    model=model,
    tools=[DuckDuckGo()],
    instructions=["Always include sources"],
    show_tool_calls=True,
    markdown=True,
)

# Financial agent
finance_agent = Agent(
    name="Finance AI Agent",
    model=model,
    tools=[
        YFinanceTools(
            stock_price=True, 
            analyst_recommendations=True, 
            stock_fundamentals=True,
            company_news=True
        ),
    ],
    instructions=["Use table to display data"],
    show_tool_calls=True,
    markdown=True,
)

# Multi-agent system combining both agents
multi_ai_agent = Agent(
    team=[web_search_agent, finance_agent],
    instructions=["Always include sources", "Use table to display data"],
    show_tool_calls=True,
    markdown=True,
)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    query = request.form.get('query', '')
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        # Get response from the multi-agent
        response = multi_ai_agent.run(query)
        response_content = response.content
# return jsonify({'response': response_content})
        return jsonify({'response': response_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create index.html file
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Financial and Web Search AI Agent</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.5/dist/purify.min.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto p-4 max-w-4xl">
        <h1 class="text-3xl font-bold mb-6 text-center text-blue-700">Financial and Web Search AI Agent</h1>
        
        <div class="mb-8 bg-white p-6 rounded-lg shadow-md">
            <form id="queryForm" class="space-y-4">
                <div>
                    <label for="query" class="block text-sm font-medium text-gray-700 mb-1">Ask a question about financial data or web search:</label>
                    <input type="text" id="query" name="query" placeholder="e.g., Summarize analyst recommendation and share the latest news for AAPL" 
                           class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <button type="submit" class="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors">
                    Ask AI
                </button>
            </form>
        </div>
        
        <div class="bg-white p-6 rounded-lg shadow-md">
            <h2 class="text-xl font-semibold mb-4 text-gray-800">Response</h2>
            <div id="loading" class="hidden">
                <div class="flex items-center justify-center">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
                    <span class="ml-2">Processing your request...</span>
                </div>
            </div>
            <div id="response" class="prose max-w-none"></div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const queryForm = document.getElementById('queryForm');
            const responseDiv = document.getElementById('response');
            const loadingDiv = document.getElementById('loading');
            
            queryForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(queryForm);
                const query = formData.get('query');
                
                if (!query) {
                    responseDiv.innerHTML = '<p class="text-red-500">Please enter a query</p>';
                    return;
                }
                
                // Show loading indicator
                loadingDiv.classList.remove('hidden');
                responseDiv.innerHTML = '';
                
                // Send request to backend
                fetch('/ask', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // Hide loading indicator
                    loadingDiv.classList.add('hidden');
                    
                    if (data.error) {
                        responseDiv.innerHTML = `<p class="text-red-500">Error: ${data.error}</p>`;
                    } else {
                        // Convert markdown to HTML and sanitize
                        const htmlContent = DOMPurify.sanitize(marked.parse(data.response));
                        responseDiv.innerHTML = htmlContent;
                    }
                })
                .catch(error => {
                    loadingDiv.classList.add('hidden');
                    responseDiv.innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
                });
            });
        });
    </script>
</body>
</html>
    ''')

if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True, port=5000)