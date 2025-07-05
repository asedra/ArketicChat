# 🚀 ATTILA AI - Quick Start Guide

Get up and running with ATTILA AI Enhanced Function Management System in minutes!

## ⚡ One-Command Setup

```bash
./setup.sh
```

This automated script will:
- ✅ Check prerequisites (Python 3.11+, Node.js 18+)
- ✅ Set up Python virtual environment
- ✅ Install all dependencies
- ✅ Create environment configuration
- ✅ Initialize database
- ✅ Create startup scripts

## 🔑 Required Configuration

1. **Add your OpenAI API key** (required for AI features):
   ```bash
   # Edit backend/.env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## 🎯 Start the System

```bash
# Start everything at once
./start_all.sh

# OR start individually
./start_backend.sh   # Backend only (port 8000)
./start_frontend.sh  # Frontend only (port 5173)
```

## 🌐 Access Points

- **🖥️ Main Interface:** http://localhost:5173
- **🔧 API Backend:** http://localhost:8000
- **📚 API Documentation:** http://localhost:8000/docs

## 🎮 Quick Demo

### 1. Open the Chat Interface
- Navigate to http://localhost:5173
- You'll see the modern AI chat interface

### 2. Try Natural Language Commands
```
"What's the weather in New York?"
"Review this Python code: print('hello')"
"Search for information about FastAPI"
```

### 3. Explore Function Management
- Click "Functions" in the sidebar
- Create, edit, and manage your functions
- Support for 5 function types: Basic, API, Prompt, Document, MCP

### 4. Watch AI Routing in Action
- The system automatically selects the best functions
- See confidence scores and reasoning
- View execution results and performance metrics

## 🔧 Function Types Overview

| Type | Description | Use Case |
|------|-------------|----------|
| **Basic** | Simple function execution | Custom logic, calculations |
| **API** | HTTP API integration | Weather, data services, webhooks |
| **Prompt** | AI-powered text processing | Code review, content generation |
| **Document** | Knowledge base search | Documentation lookup, Q&A |
| **MCP** | Model Context Protocol | Advanced AI tool integration |

## 📋 Example Functions

### Weather API Function
```json
{
  "name": "Weather Check",
  "type": "api",
  "parameters": {"location": "string"},
  "api_config": {
    "method": "GET",
    "endpoint": "https://api.openweathermap.org/data/2.5/weather",
    "authentication": {
      "type": "api_key",
      "api_key": "${WEATHER_API_KEY}",
      "header_name": "X-API-Key"
    }
  }
}
```

### Code Review Prompt Function
```json
{
  "name": "Code Review",
  "type": "prompt",
  "parameters": {"code": "string", "language": "string"},
  "prompt_template": "Please review this {{language}} code and provide feedback:\n\n{{code}}\n\nProvide: 1) Overall assessment 2) Issues found 3) Improvements 4) Security considerations"
}
```

### Document Search Function
```json
{
  "name": "Documentation Search",
  "type": "document",
  "parameters": {"query": "string"},
  "document_content": "Your knowledge base content here..."
}
```

## 🛠️ Development Tools

```bash
# Reset database
./reset_database.sh

# Test API endpoints
./test_api.sh

# View logs
tail -f backend/logs/app.log
```

## 📊 Key Features

- **🧠 AI-Powered Routing** - Automatically selects optimal functions
- **⚡ Sub-2s Execution** - Fast performance with parallel processing
- **🔄 Multi-Function Orchestration** - Chain and combine functions
- **📈 Real-time Analytics** - Performance metrics and usage tracking
- **🎨 Modern UI** - Responsive design with dark/light themes
- **🔒 Secure** - Authentication, validation, and error handling

## 🆘 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :5173

# Kill processes if needed
kill -9 <PID>
```

**OpenAI API errors:**
- Verify your API key in `backend/.env`
- Check your OpenAI account has credits
- Ensure the key has proper permissions

**Database issues:**
```bash
# Reset and reinitialize
./reset_database.sh
```

**Python dependency issues:**
```bash
cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 📖 Next Steps

1. **Explore the Functions Page** - Create custom functions
2. **Test Different Function Types** - Try API, Prompt, Document functions
3. **Review Analytics** - Check performance metrics
4. **Read Documentation** - Dive deeper with docs/ folder
5. **Check Examples** - See PHASE_4_COMPLETION_REPORT.md

## 🎓 Learning Resources

- **📚 Full Documentation:** `docs/` folder
- **🏗️ Architecture Guide:** `docs/01_Technical_Architecture.md`
- **🔧 API Reference:** `docs/05_API_Documentation.md`
- **📈 Performance Guide:** `docs/08_Performance_Optimization_Guide.md`

## 🔗 Useful Links

- **OpenAI API Keys:** https://platform.openai.com/api-keys
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SvelteKit Guide:** https://kit.svelte.dev/
- **Tailwind CSS:** https://tailwindcss.com/

---

**🎉 You're all set!** ATTILA AI is ready to revolutionize your function management with intelligent AI routing and seamless orchestration.

Need help? Check the documentation or create an issue on GitHub!