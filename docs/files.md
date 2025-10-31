# File index

- example.env       env var descriptions and defaults

## src

### mcp_knowledge_graph     Main package

    - __init__.py           
    - __main__.py           main entry point of package
    - manager.py            knowledge graph interactions
    - models.py             data models
    - notify.py             supabase integration
    - server.py             main tool logic
    - settings.py           settings handlers
    - visualize.py          experimental visualizer
    - logger.py             centralized logging config

#### utils
    - migrate_graph.py      experimental memory migration tool
    - schema.md             high-level knowledge graph schema
    - seed_graph.py         util to create a new default graph from scratch
