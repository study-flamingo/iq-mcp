🔍 Scanning local project: .
📊 Based on vulnerablemcp.info, HiddenLayer, Invariant Labs, and Trail of Bits research

🔑 Scanning for credential vulnerabilities...
🧪 Scanning for tool poisoning vulnerabilities...
🎯 Scanning for parameter injection vulnerabilities...
💉 Scanning for prompt injection vulnerabilities...
🔄 Scanning for tool mutation vulnerabilities...
💬 Scanning for conversation exfiltration vulnerabilities...
🎨 Scanning for ANSI escape injection vulnerabilities...
📋 Scanning for MCP protocol violations...
🛡️ Scanning for input validation issues...
🎭 Scanning for server spoofing vulnerabilities...
🌊 Scanning for toxic agent flows...
🔐 Scanning for permission and access control issues...
{
  "projectPath": ".",
  "scanDate": "2026-01-09T17:47:05.477Z",
  "scanner": "MCP Watch",
  "researchSources": [
    "VulnerableMCP Database",
    "HiddenLayer Research",
    "Invariant Labs Research",
    "Trail of Bits Research",
    "PromptHub Analysis"
  ],
  "totalVulnerabilities": 137,
  "severityCounts": {
    "critical": 6,
    "high": 37,
    "medium": 94
  },
  "categoryCounts": {
    "credential-leak": 3,
    "prompt-injection": 1,
    "input-validation": 2,
    "server-spoofing": 1,
    "toxic-flow": 100,
    "access-control": 30
  },
  "vulnerabilities": [
    {
      "id": "HARDCODED_CREDENTIALS",
      "severity": "critical",
      "category": "credential-leak",
      "message": "Hardcoded credentials detected",
      "file": ".env",
      "line": 10,
      "evidence": "IQ_API_KEY=iqmcp-sk-***REDACTED***",
      "source": "Trail of Bits research"
    },
    {
      "id": "HARDCODED_CREDENTIALS",
      "severity": "critical",
      "category": "credential-leak",
      "message": "Hardcoded credentials detected",
      "file": "AGENTS.md",
      "line": 9,
      "evidence": "- **API Key:** `iqmcp-sk-***REDACTED***`",
      "source": "Trail of Bits research"
    },
    {
      "id": "HARDCODED_CREDENTIALS",
      "severity": "critical",
      "category": "credential-leak",
      "message": "Hardcoded credentials detected",
      "file": "AGENTS.md",
      "line": 88,
      "evidence": "\"Authorization\": \"Bearer iqmcp-sk-***REDACTED***\"",
      "source": "Trail of Bits research"
    },
    {
      "id": "RETRIEVAL_AGENT_DECEPTION",
      "severity": "high",
      "category": "prompt-injection",
      "message": "RADE pattern detected - hidden commands in retrieval content",
      "file": "docs\\ROADMAP.md",
      "line": 356,
      "evidence": "- **Modularity**: Optional features (integrations, semantic search) can be enabled/disabled without affecting core",
      "source": "PromptHub research"
    },
    {
      "id": "PATH_TRAVERSAL",
      "severity": "high",
      "category": "input-validation",
      "message": "Path traversal vulnerability - accesses files outside directory",
      "file": "src\\mcp_knowledge_graph\\supabase_utils.py",
      "line": 39,
      "evidence": "f\"Local manager initialized, loading graph from local JSONL file at '{settings.memory_path}'...\"",
      "source": "PromptHub research (22% affected)"
    },
    {
      "id": "PATH_TRAVERSAL",
      "severity": "high",
      "category": "input-validation",
      "message": "Path traversal vulnerability - accesses files outside directory",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\vite.config.js",
      "line": 9,
      "evidence": "outDir: '../static',",
      "source": "PromptHub research (22% affected)"
    },
    {
      "id": "SUSPICIOUS_SERVER_NAME",
      "severity": "medium",
      "category": "server-spoofing",
      "message": "Server name mimics popular service - potential spoofing",
      "file": "src\\mcp_knowledge_graph\\visualize.py",
      "evidence": "Server name resembles trusted service",
      "source": "PromptHub research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 5,
      "evidence": "For single-user deployments, uses StaticTokenVerifier with API keys.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 24,
      "evidence": "AuthProvider instance if IQ_API_KEY is set, None otherwise.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 27,
      "evidence": "IQ_API_KEY: The API key required for authentication.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 31,
      "evidence": "Set IQ_API_KEY in your environment or .env file:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 32,
      "evidence": "IQ_API_KEY=iqmcp-sk-your-secret-key",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 37,
      "evidence": "api_key = os.getenv(\"IQ_API_KEY\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 39,
      "evidence": "if not api_key:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 41,
      "evidence": "\"⚠️  IQ_API_KEY not set - server will run WITHOUT authentication! \"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 42,
      "evidence": "\"Set IQ_API_KEY for production deployments.\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 60,
      "evidence": "api_key: {",
      "source": "Invariant Labs research"
    },
    {
      "id": "GENERIC_TOXIC_FLOW_CHAIN",
      "severity": "critical",
      "category": "toxic-flow",
      "message": "Complete toxic flow: external input → privileged access → public output",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "evidence": "File contains external input processing, privileged data access, and public output mechanisms",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 294,
      "evidence": "Verify that the relation endpoints exist in the graph. If the entities themselves are",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 305,
      "evidence": "- ValueError if the relation is missing one or both endpoint IDs",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 313,
      "evidence": "f\"Relation `A {relation.relation} B` is missing one or both endpoint IDs!\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 327,
      "evidence": "f\"Relation `{relation.relation}` has invalid endpoints: {relation.from_id} and {relation.to_id}\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 343,
      "evidence": "raise ValueError(f\"Relation {relation.relation} missing one or both endpoint IDs!\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 1319,
      "evidence": "f\"Could not resolve relation endpoints for deletion: from={rel.from_id or rel.from_entity}, to={rel.to_id or rel.to_entity}\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 1340,
      "evidence": "Search for nodes in the knowledge graph based on a query.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 1356,
      "evidence": "query_lower = query.lower()",
      "source": "Invariant Labs research"
    },
    {
      "id": "GENERIC_TOXIC_FLOW_CHAIN",
      "severity": "critical",
      "category": "toxic-flow",
      "message": "Complete toxic flow: external input → privileged access → public output",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "evidence": "File contains external input processing, privileged data access, and public output mechanisms",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\middleware.py",
      "line": 25,
      "evidence": "GET /iq?token=your-api-key",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\middleware.py",
      "line": 28,
      "evidence": "Authorization: Bearer your-api-key",
      "source": "Invariant Labs research"
    },
    {
      "id": "AUTOMATIC_CONTENT_PUBLISHING",
      "severity": "high",
      "category": "toxic-flow",
      "message": "Automatic content publishing - data exfiltration risk",
      "file": "src\\mcp_knowledge_graph\\models.py",
      "line": 430,
      "evidence": "\"\"\"Create a relation from one entity object to another with the given relation content.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\models.py",
      "line": 470,
      "evidence": "Includes endpoint names for backward compatibility, relation content (by alias), and",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\models.py",
      "line": 1197,
      "evidence": "\"\"\"Ensure at least one identifier is provided for each endpoint.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "AUTOMATIC_CONTENT_PUBLISHING",
      "severity": "high",
      "category": "toxic-flow",
      "message": "Automatic content publishing - data exfiltration risk",
      "file": "src\\mcp_knowledge_graph\\models.py",
      "line": 1213,
      "evidence": "\"\"\"Produce a CreateRelationRequest from Entity objects and relation content.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 90,
      "evidence": "# Auth is configured via IQ_API_KEY environment variable",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 544,
      "evidence": "- include_observations: Include observations related to the user in the response.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 545,
      "evidence": "- include_relations: Include relations related to the user in the response.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 649,
      "evidence": "- include_observations: Include observations related to the user in the response.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 650,
      "evidence": "- include_relations: Include relations related to the user in the response.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1095,
      "evidence": "required fields from their response.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1189,
      "evidence": "\"\"\"Search for nodes in the knowledge graph based on a query.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1706,
      "evidence": "# If HTTP transport, mount web UI alongside MCP endpoints",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1723,
      "evidence": "logger.info(f\"📍 MCP endpoint configured at: {mcp_path}\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "AUTOMATIC_CONTENT_PUBLISHING",
      "severity": "high",
      "category": "toxic-flow",
      "message": "Automatic content publishing - data exfiltration risk",
      "file": "src\\mcp_knowledge_graph\\settings.py",
      "line": 99,
      "evidence": "Create a IQ-MCP Settings instance from CLI args, env, and defaults.",
      "source": "Invariant Labs research"
    },
    {
      "id": "GENERIC_TOXIC_FLOW_CHAIN",
      "severity": "critical",
      "category": "toxic-flow",
      "message": "Complete toxic flow: external input → privileged access → public output",
      "file": "src\\mcp_knowledge_graph\\settings.py",
      "evidence": "File contains external input processing, privileged data access, and public output mechanisms",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 120,
      "evidence": "query = query.eq(\"reviewed\", \"false\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 122,
      "evidence": "query = query.gte(\"received_at\", from_ts)",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 124,
      "evidence": "query = query.lte(\"received_at\", to_ts)",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 125,
      "evidence": "response = query.execute()",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 129,
      "evidence": "for row in response.data:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 263,
      "evidence": "# Relations: dedupe by (from_id, to_id, relation) and keep only those whose endpoints exist",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 444,
      "evidence": "for row in observations_response.data:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 457,
      "evidence": "for row in entities_response.data:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 480,
      "evidence": "for row in relations_response.data:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\supabase_manager.py",
      "line": 492,
      "evidence": "for row in user_info_response.data:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\visualize.py",
      "line": 364,
      "evidence": "if not args.input.exists():",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 5,
      "evidence": "the graph visualizer and API endpoints.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 9,
      "evidence": "from fastapi import HTTPException, Security",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 10,
      "evidence": "from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 21,
      "evidence": "\"\"\"Get the expected API key from environment or context.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 27,
      "evidence": "# Fall back to the main API key",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 28,
      "evidence": "token = os.getenv(\"IQ_API_KEY\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\auth.py",
      "line": 51,
      "evidence": "logger.warning(\"⚠️  No IQ_GRAPH_JWT_TOKEN or IQ_API_KEY set - web access is UNPROTECTED!\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 7,
      "evidence": "const urlToken = params.get('token');",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 21,
      "evidence": "const api = axios.create({",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 22,
      "evidence": "baseURL: '/api',",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 29,
      "evidence": "api.interceptors.request.use((config) => {",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 38,
      "evidence": "api.interceptors.response.use(",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 49,
      "evidence": "export const graphApi = {",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 52,
      "evidence": "const response = await api.get('/graph/data');",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 53,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 58,
      "evidence": "const response = await api.post('/graph/entity', entity);",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 59,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 63,
      "evidence": "const response = await api.patch(`/graph/entity/${entityId}`, updates);",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 64,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 68,
      "evidence": "const response = await api.delete(`/graph/entity/${entityId}`);",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 69,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 74,
      "evidence": "const response = await api.post('/graph/relation', relation);",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 75,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 79,
      "evidence": "const response = await api.delete('/graph/relation', {",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 82,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 87,
      "evidence": "const response = await api.post(`/graph/entity/${entityId}/observations`, observations);",
      "source": "Invariant Labs research"
    },
    {
      "id": "AUTOMATIC_CONTENT_PUBLISHING",
      "severity": "high",
      "category": "toxic-flow",
      "message": "Automatic content publishing - data exfiltration risk",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 87,
      "evidence": "const response = await api.post(`/graph/entity/${entityId}/observations`, observations);",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 88,
      "evidence": "return response.data;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\src\\api\\graphApi.js",
      "line": 92,
      "evidence": "export default api;",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\frontend\\vite.config.js",
      "line": 15,
      "evidence": "'/api': {",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 2,
      "evidence": "FastAPI routes for the graph visualizer web interface.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 4,
      "evidence": "Provides REST API endpoints for graph data retrieval and manipulation,",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 8,
      "evidence": "from fastapi import FastAPI, HTTPException, Depends, Response",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 9,
      "evidence": "from fastapi.responses import HTMLResponse, FileResponse, JSONResponse",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 10,
      "evidence": "from fastapi.staticfiles import StaticFiles",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 40,
      "evidence": "\"\"\"Web API model for creating entities.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 49,
      "evidence": "\"\"\"Web API model for updating entities.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 58,
      "evidence": "\"\"\"Web API model for creating relations.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 64,
      "evidence": "def create_web_app(manager: KnowledgeGraphManager) -> FastAPI:",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 66,
      "evidence": "Create the FastAPI application for the web interface.",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 72,
      "evidence": "FastAPI application",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 74,
      "evidence": "app = FastAPI(",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 93,
      "evidence": "\"\"\"Health check endpoint.\"\"\"",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 132,
      "evidence": "@app.get(\"/api/graph/data\", response_model=GraphDataResponse)",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 192,
      "evidence": "@app.post(\"/api/graph/entity\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 251,
      "evidence": "@app.patch(\"/api/graph/entity/{entity_id}\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 286,
      "evidence": "@app.delete(\"/api/graph/entity/{entity_id}\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 303,
      "evidence": "@app.post(\"/api/graph/relation\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 343,
      "evidence": "@app.delete(\"/api/graph/relation\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 374,
      "evidence": "@app.post(\"/api/graph/entity/{entity_id}/observations\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "src\\mcp_knowledge_graph\\web\\routes.py",
      "line": 418,
      "evidence": "logger.info(\"✅ Web API routes configured\")",
      "source": "Invariant Labs research"
    },
    {
      "id": "UNTRUSTED_DATA_PROCESSING",
      "severity": "medium",
      "category": "toxic-flow",
      "message": "External data processed without sanitization",
      "file": "tests\\test_graph.py",
      "line": 458,
      "evidence": "# Delete by creating a Relation with the same endpoints but using names",
      "source": "Invariant Labs research"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "AGENTS.md",
      "line": 60,
      "evidence": "- **Enhanced `update_user_info`**: Added optional `observations` parameter",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\CHANGELOG.md",
      "line": 31,
      "evidence": "- **Enhanced `update_user_info` Tool**: Now supports adding observations in the same call",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\CHANGELOG.md",
      "line": 239,
      "evidence": "# Update user info and add observations in one call",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\CHANGELOG.md",
      "line": 240,
      "evidence": "update_user_info(",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\DEVELOPMENT.md",
      "line": 465,
      "evidence": "4. ✅ CHANGELOG.md updated (if user-facing changes)",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\PROJECT_OVERVIEW.md",
      "line": 97,
      "evidence": "| `update_user_info` | Update user identifying information |",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\ROADMAP.md",
      "line": 142,
      "evidence": "- Direct parameter passing eliminates need for separate `update_user_info` calls",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\WORKFLOWS.md",
      "line": 82,
      "evidence": "- Tool: `server.update_user_info`",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "docs\\WORKFLOWS.md",
      "line": 83,
      "evidence": "- Manager: `manager.update_user_info(UserIdentifier)`",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "README.md",
      "line": 122,
      "evidence": "| `update_user_info` | Update user identifying information (optionally add observations) |",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\auth.py",
      "line": 62,
      "evidence": "\"scopes\": [\"read\", \"write\", \"admin\"],",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 1727,
      "evidence": "async def update_user_info(self, new_user_info: UserIdentifier) -> UserIdentifier:",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\manager.py",
      "line": 1728,
      "evidence": "\"\"\"Update the user's identifying information in the graph.",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\models.py",
      "line": 740,
      "evidence": "# Create the user info object",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 77,
      "evidence": "- update_user_info(new_user_info) -> UserIdentifier",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1025,
      "evidence": "async def update_user_info(  # NOTE: feels weird, re-evaluate",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1057,
      "evidence": "Update the user's identifying information in the graph. This tool should be rarely called, and",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1089,
      "evidence": "On success, the updated user info.",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1133,
      "evidence": "updated_user_info = await manager.update_user_info(new_user_info)",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1140,
      "evidence": "user_entity_id = updated_user_info.linked_entity_id",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1144,
      "evidence": "# Create observation requests for the user entity",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1162,
      "evidence": "f\"Updated user info and added {len(observations)} observation(s):\\n\"",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1168,
      "evidence": "result_str = \"Updated user info, but failed to add observations:\\n\"",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1174,
      "evidence": "result_str = f\"Updated user info, but failed to add observations: {e}\\n\"",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1176,
      "evidence": "result_str = str(updated_user_info)",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\server.py",
      "line": 1180,
      "evidence": "raise ToolError(f\"Failed to update user info: {e}\")",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "src\\mcp_knowledge_graph\\utils\\migrate_graph.py",
      "line": 158,
      "evidence": "print(f\"Updated line {i}: User info: {new_user_info}\")",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "tests\\test_graph.py",
      "line": 467,
      "evidence": "async def test_update_user_info_with_observations(mock_context):",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "tests\\test_graph.py",
      "line": 475,
      "evidence": "# Update user info with observations",
      "source": "Security best practices"
    },
    {
      "id": "EXCESSIVE_PERMISSIONS",
      "severity": "high",
      "category": "access-control",
      "message": "Excessive permissions - violates least privilege",
      "file": "tests\\test_graph.py",
      "line": 484,
      "evidence": "updated = await mgr.update_user_info(new_user_info)",
      "source": "Security best practices"
    }
  ]
}

❌ Found 43 critical/high severity vulnerabilities
🚨 Immediate action required!
