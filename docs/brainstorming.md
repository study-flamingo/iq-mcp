1. Core Value Proposition
- Temporal observations with durability (smart memory management)
- Project/task/conversational context awareness (automatic current project detection)
- Knowledge graph structure (entities + relations)
- Memory visualization and manual management
- Integration with user data sources such as email, calendar, slack, zapier, etc.

2. Out of scope
- Multi-user support (will revisit in 2.0.0)
- Plugins ecosystem - plugins will really be optional features that ship with the product
- AI-powered insights (insights would come from the MCP client LLM, not this app)
- Collaboration (doesn't make sense yet)

3. Must-have features
- Project & Task Management (v1.5.0)
- Enhanced and semantic Search (full-text, filters, query DSL, embeddings, etc.)
- Backup options beyond the current .JSONL local storage
- Export/Import (data portability)

4. Target users
- Me!
- Individual users who want a memory system that is system-agnostic, can track tasks/projects, and can provide different sets of context depending on what is relevant to the user's requests (project management)

5. Feature Philosophy
- Modularity: A robust core that can easily interact with optional features depending on user preferences or use-case

6. Client agnosticism
- Data portability and progressive enhancement
