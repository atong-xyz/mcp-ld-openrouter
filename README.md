# mcp-ld-openrouter
Sample Demo to use LaunchDarkly MCP server with OpenRouter
What you need to do

Activate the .venv that uv created before running your script.

Run these commands in your project directory:

# Activate the virtual environment (Linux/macOS)

```
python3 -m venv .venv

source .venv/bin/activate
```

# Install dependencies from pyproject.toml

```
pip install .
```

# Now run your script inside the venv

```
python mcp-server-launchdarkly.py
```

# .env
Remember to create a `.env` file within your project

```
OPENAI_API_KEY = '<YOUR-OPENROUTER-API-KEY>'
MODEL = "google/gemini-2.0-flash-001" example - can select different models from OpenRouter

LD_API_KEY = "<YOUR-LAUNCHDARKLY-API-KEY>"

```
