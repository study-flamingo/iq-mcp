"""
FastAPI routes for the graph visualizer web interface.

Provides REST API endpoints for graph data retrieval and manipulation,
as well as serving the React frontend.
"""

from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from pathlib import Path
import json

import os

from ..iq_logging import logger
from ..context import ctx
from ..manager import KnowledgeGraphManager
from ..models import (
    CreateEntityRequest,
    CreateRelationRequest,
    ObservationRequest,
    Observation,
    DurabilityType,
    Entity,
    Relation,
)
from .auth import verify_token


# Request/Response models
class GraphDataResponse(BaseModel):
    """Response model for graph data."""
    nodes: List[dict]
    edges: List[dict]
    user_info: dict


class CreateEntityRequestWeb(BaseModel):
    """Web API model for creating entities."""
    name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    observations: Optional[List[dict]] = Field(default=None, description="List of observations")
    aliases: Optional[List[str]] = Field(default=None, description="List of aliases")
    icon: Optional[str] = Field(default=None, description="Emoji icon")


class UpdateEntityRequestWeb(BaseModel):
    """Web API model for updating entities."""
    name: Optional[str] = Field(default=None, description="New entity name")
    entity_type: Optional[str] = Field(default=None, description="New entity type")
    aliases: Optional[List[str]] = Field(default=None, description="Aliases to add/replace")
    icon: Optional[str] = Field(default=None, description="Emoji icon")
    merge_aliases: bool = Field(default=True, description="Merge or replace aliases")


class CreateRelationRequestWeb(BaseModel):
    """Web API model for creating relations."""
    from_entity: str = Field(..., description="Source entity (ID or name)")
    to_entity: str = Field(..., description="Target entity (ID or name)")
    relation: str = Field(..., description="Relation description")


def create_web_app(manager: KnowledgeGraphManager) -> FastAPI:
    """
    Create the FastAPI application for the web interface.

    Args:
        manager: Knowledge graph manager instance

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="IQ-MCP Graph Visualizer",
        description="Interactive knowledge graph visualization and editing",
        version="1.0.0",
    )

    # Mount static files (will be created by React build)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"📁 Mounted static files from {static_dir}")
    else:
        logger.warning(f"⚠️  Static directory not found: {static_dir}")


    # ==================== PUBLIC ROUTES ====================

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "iq-mcp-web"}


    @app.get("/oauth/consent", response_class=HTMLResponse)
    async def oauth_consent_page(authorization_id: str = None):
        """
        OAuth consent page for Claude Desktop/Mobile authorization.

        This page is displayed to users when an OAuth client (like Claude)
        requests authorization. Users can approve or deny the request.

        Query params:
            authorization_id: The Supabase authorization request ID
        """
        # Get Supabase project URL and anon key from environment
        supabase_url = os.getenv("IQ_SUPABASE_AUTH_PROJECT_URL", "")
        supabase_anon_key = os.getenv("IQ_SUPABASE_ANON_KEY", "")

        if not supabase_url or not supabase_anon_key:
            missing = []
            if not supabase_url:
                missing.append("IQ_SUPABASE_AUTH_PROJECT_URL")
            if not supabase_anon_key:
                missing.append("IQ_SUPABASE_ANON_KEY")
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>OAuth Error</title></head>
                <body style="font-family: system-ui, sans-serif; padding: 40px; max-width: 500px; margin: 0 auto; text-align: center;">
                    <h1>OAuth Not Configured</h1>
                    <p>Supabase OAuth is not configured on this server.</p>
                    <p>Missing: {', '.join(missing)}</p>
                    <p>Please contact the administrator.</p>
                </body>
                </html>
                """,
                status_code=500
            )

        # Serve the consent page HTML with Supabase JS SDK
        consent_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authorize Application - IQ-MCP</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .consent-card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            padding: 40px;
            max-width: 450px;
            width: 100%;
        }}
        .logo {{
            font-size: 48px;
            text-align: center;
            margin-bottom: 24px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #1a1a2e;
            text-align: center;
            margin-bottom: 8px;
        }}
        .subtitle {{
            color: #666;
            text-align: center;
            margin-bottom: 32px;
        }}
        .client-info {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .client-name {{
            font-weight: 600;
            font-size: 18px;
            color: #1a1a2e;
            margin-bottom: 8px;
        }}
        .client-id {{
            font-size: 12px;
            color: #888;
            font-family: monospace;
            word-break: break-all;
        }}
        .scopes-section {{
            margin-bottom: 24px;
        }}
        .scopes-title {{
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 12px;
        }}
        .scope-item {{
            display: flex;
            align-items: center;
            padding: 12px;
            background: #f0f4f8;
            border-radius: 8px;
            margin-bottom: 8px;
        }}
        .scope-icon {{
            margin-right: 12px;
            font-size: 20px;
        }}
        .scope-text {{
            color: #333;
        }}
        .buttons {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }}
        button {{
            flex: 1;
            padding: 14px 24px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }}
        .approve-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .approve-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .deny-btn {{
            background: #e9ecef;
            color: #495057;
        }}
        .deny-btn:hover {{
            background: #dee2e6;
        }}
        button:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }}
        .loading {{
            text-align: center;
            padding: 60px 20px;
        }}
        .spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid #e9ecef;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .error {{
            background: #fee2e2;
            color: #dc2626;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }}
        .success {{
            background: #d1fae5;
            color: #059669;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .login-prompt {{
            text-align: center;
            padding: 20px;
        }}
        .login-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 100%;
        }}
    </style>
</head>
<body>
    <div class="consent-card">
        <div id="content">
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading authorization request...</p>
            </div>
        </div>
    </div>

    <script>
        const SUPABASE_URL = '{supabase_url}';
        const SUPABASE_ANON_KEY = '{supabase_anon_key}';

        const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

        const urlParams = new URLSearchParams(window.location.search);
        const authorizationId = urlParams.get('authorization_id');

        const contentDiv = document.getElementById('content');

        function showError(message) {{
            contentDiv.innerHTML = `
                <div class="logo">⚠️</div>
                <h1>Authorization Error</h1>
                <div class="error" style="margin-top: 20px;">${{message}}</div>
            `;
        }}

        function showSuccess(message) {{
            contentDiv.innerHTML = `
                <div class="logo">✅</div>
                <h1>Success</h1>
                <div class="success" style="margin-top: 20px;">${{message}}</div>
                <p style="text-align: center; margin-top: 16px; color: #666;">You can close this window.</p>
            `;
        }}

        function showLoginPrompt() {{
            contentDiv.innerHTML = `
                <div class="logo">🔐</div>
                <h1>Sign In Required</h1>
                <p class="subtitle">Please sign in to authorize this application.</p>
                <div class="login-prompt">
                    <button class="login-btn" onclick="signIn()">Sign In with Supabase</button>
                </div>
            `;
        }}

        async function signIn() {{
            const {{ error }} = await supabase.auth.signInWithOAuth({{
                provider: 'github',
                options: {{
                    redirectTo: window.location.href
                }}
            }});
            if (error) {{
                showError(error.message);
            }}
        }}

        function showConsentForm(authDetails) {{
            const clientName = authDetails.client?.name || authDetails.client_name || 'Unknown Application';
            const clientId = authDetails.client?.client_id || authDetails.client_id || '';
            const scopes = authDetails.scopes || authDetails.scope?.split(' ') || ['read', 'write'];

            const scopeIcons = {{
                'read': '📖',
                'write': '✏️',
                'admin': '👑',
                'openid': '🔑',
                'profile': '👤',
                'email': '📧',
                'offline_access': '🔄'
            }};

            const scopeDescriptions = {{
                'read': 'Read your knowledge graph data',
                'write': 'Create and modify knowledge graph entries',
                'admin': 'Full administrative access',
                'openid': 'Verify your identity',
                'profile': 'Access your profile information',
                'email': 'Access your email address',
                'offline_access': 'Stay connected when you\\'re not using the app'
            }};

            const scopesHtml = scopes.map(scope => `
                <div class="scope-item">
                    <span class="scope-icon">${{scopeIcons[scope] || '📋'}}</span>
                    <span class="scope-text">${{scopeDescriptions[scope] || scope}}</span>
                </div>
            `).join('');

            contentDiv.innerHTML = `
                <div class="logo">🧠</div>
                <h1>Authorize Application</h1>
                <p class="subtitle">An application wants to access your IQ-MCP account</p>

                <div class="client-info">
                    <div class="client-name">${{clientName}}</div>
                    <div class="client-id">${{clientId}}</div>
                </div>

                <div class="scopes-section">
                    <div class="scopes-title">This application will be able to:</div>
                    ${{scopesHtml}}
                </div>

                <div class="buttons">
                    <button class="deny-btn" id="denyBtn" onclick="denyAuth()">Deny</button>
                    <button class="approve-btn" id="approveBtn" onclick="approveAuth()">Approve</button>
                </div>
            `;
        }}

        async function approveAuth() {{
            const approveBtn = document.getElementById('approveBtn');
            const denyBtn = document.getElementById('denyBtn');
            approveBtn.disabled = true;
            denyBtn.disabled = true;
            approveBtn.textContent = 'Approving...';

            try {{
                // Call Supabase to approve the authorization
                const {{ data, error }} = await supabase.functions.invoke('oauth-authorize', {{
                    body: {{
                        authorization_id: authorizationId,
                        action: 'approve'
                    }}
                }});

                if (error) throw error;

                // If there's a redirect URL, redirect the user
                if (data?.redirect_uri) {{
                    window.location.href = data.redirect_uri;
                }} else {{
                    showSuccess('Authorization approved! The application can now access your account.');
                }}
            }} catch (error) {{
                console.error('Approve error:', error);
                showError('Failed to approve authorization: ' + error.message);
            }}
        }}

        async function denyAuth() {{
            const approveBtn = document.getElementById('approveBtn');
            const denyBtn = document.getElementById('denyBtn');
            approveBtn.disabled = true;
            denyBtn.disabled = true;
            denyBtn.textContent = 'Denying...';

            try {{
                const {{ data, error }} = await supabase.functions.invoke('oauth-authorize', {{
                    body: {{
                        authorization_id: authorizationId,
                        action: 'deny'
                    }}
                }});

                if (error) throw error;

                if (data?.redirect_uri) {{
                    window.location.href = data.redirect_uri;
                }} else {{
                    showSuccess('Authorization denied. The application will not be able to access your account.');
                }}
            }} catch (error) {{
                console.error('Deny error:', error);
                showError('Failed to deny authorization: ' + error.message);
            }}
        }}

        async function init() {{
            if (!authorizationId) {{
                showError('Missing authorization_id parameter');
                return;
            }}

            try {{
                // Check if user is logged in
                const {{ data: {{ user }} }} = await supabase.auth.getUser();

                if (!user) {{
                    showLoginPrompt();
                    return;
                }}

                // Get authorization details from Supabase
                const {{ data, error }} = await supabase.functions.invoke('oauth-get-authorization', {{
                    body: {{ authorization_id: authorizationId }}
                }});

                if (error) throw error;

                showConsentForm(data);

            }} catch (error) {{
                console.error('Init error:', error);
                // Fallback: show a generic consent form
                showConsentForm({{
                    client_name: 'Claude',
                    client_id: authorizationId,
                    scopes: ['read', 'write']
                }});
            }}
        }}

        init();
    </script>
</body>
</html>
        """

        return HTMLResponse(content=consent_html)


    # ==================== PROTECTED ROUTES ====================

    @app.get("/graph", response_class=HTMLResponse)
    async def serve_graph_ui(token: str = Depends(verify_token)):
        """
        Serve the React-based graph visualizer UI.

        Requires authentication via Authorization: Bearer <token>
        """
        index_path = static_dir / "index.html"

        if not index_path.exists():
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head><title>Graph Visualizer - Not Built</title></head>
                <body style="font-family: sans-serif; padding: 40px; max-width: 600px; margin: 0 auto;">
                    <h1>⚠️ Frontend Not Built</h1>
                    <p>The React frontend has not been built yet.</p>
                    <p>Please run:</p>
                    <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
cd src/mcp_knowledge_graph/web/frontend
npm install
npm run build</pre>
                    <p>Then restart the server.</p>
                </body>
                </html>
                """,
                status_code=503
            )

        return FileResponse(index_path)


    @app.get("/api/graph/data", response_model=GraphDataResponse)
    async def get_graph_data(token: str = Depends(verify_token)):
        """
        Get the complete graph data as JSON.

        Returns nodes (entities) and edges (relations) in a format
        suitable for Cytoscape.js visualization.
        """
        try:
            graph = await manager.read_graph()

            # Convert entities to Cytoscape node format
            nodes = []
            for entity in graph.entities:
                node = {
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "observations": [
                        {
                            "content": obs.content,
                            "durability": obs.durability.value,
                            "timestamp": obs.timestamp.isoformat(),
                        }
                        for obs in entity.observations
                    ],
                    "aliases": entity.aliases or [],
                    "icon": entity.icon or "",
                    "observation_count": len(entity.observations),
                }
                nodes.append(node)

            # Convert relations to Cytoscape edge format
            edges = []
            for relation in graph.relations:
                edge = {
                    "id": f"{relation.from_id}-{relation.to_id}-{relation.relation}",
                    "source": relation.from_id,
                    "target": relation.to_id,
                    "relation": relation.relation,
                }
                edges.append(edge)

            # User info
            user_info = {
                "preferred_name": graph.user_info.preferred_name,
                "linked_entity_id": graph.user_info.linked_entity_id,
            }

            return GraphDataResponse(
                nodes=nodes,
                edges=edges,
                user_info=user_info
            )

        except Exception as e:
            logger.error(f"Error fetching graph data: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/graph/entity")
    async def create_entity(
        entity: CreateEntityRequestWeb,
        token: str = Depends(verify_token)
    ):
        """
        Create a new entity in the graph.
        """
        try:
            # Convert observations from dict to Observation objects
            observations = []
            if entity.observations:
                for obs_dict in entity.observations:
                    obs = Observation(
                        content=obs_dict.get("content", ""),
                        durability=DurabilityType(obs_dict.get("durability", "short-term")),
                    )
                    observations.append(obs)

            # Create the entity request
            request = CreateEntityRequest(
                name=entity.name,
                entity_type=entity.entity_type,
                observations=observations,
                aliases=entity.aliases,
                icon=entity.icon,
            )

            # Create entity using manager
            results = await manager.create_entities([request])
            result = results[0]

            if result.errors:
                raise HTTPException(status_code=400, detail=result.errors)

            # Return the created entity
            created_entity = result.entity
            return {
                "success": True,
                "entity": {
                    "id": created_entity.id,
                    "name": created_entity.name,
                    "entity_type": created_entity.entity_type,
                    "observations": [
                        {"content": o.content, "durability": o.durability.value}
                        for o in created_entity.observations
                    ],
                    "aliases": created_entity.aliases,
                    "icon": created_entity.icon,
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.patch("/api/graph/entity/{entity_id}")
    async def update_entity(
        entity_id: str,
        updates: UpdateEntityRequestWeb,
        token: str = Depends(verify_token)
    ):
        """
        Update an existing entity.
        """
        try:
            updated = await manager.update_entity(
                entity_id=entity_id,
                name=updates.name,
                entity_type=updates.entity_type,
                aliases=updates.aliases,
                icon=updates.icon,
                merge_aliases=updates.merge_aliases,
            )

            return {
                "success": True,
                "entity": {
                    "id": updated.id,
                    "name": updated.name,
                    "entity_type": updated.entity_type,
                    "aliases": updated.aliases,
                    "icon": updated.icon,
                }
            }

        except Exception as e:
            logger.error(f"Error updating entity {entity_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.delete("/api/graph/entity/{entity_id}")
    async def delete_entity(
        entity_id: str,
        token: str = Depends(verify_token)
    ):
        """
        Delete an entity from the graph.
        """
        try:
            await manager.delete_entities(entity_ids=[entity_id])
            return {"success": True, "deleted_id": entity_id}

        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/graph/relation")
    async def create_relation(
        relation: CreateRelationRequestWeb,
        token: str = Depends(verify_token)
    ):
        """
        Create a new relation between entities.
        """
        try:
            # Create relation request
            request = CreateRelationRequest(
                from_entity_name=relation.from_entity,
                to_entity_name=relation.to_entity,
                relation=relation.relation,
            )

            # Create relation using manager
            result = await manager.create_relations([request])

            if not result.relations:
                raise HTTPException(status_code=400, detail="Failed to create relation")

            created = result.relations[0]
            return {
                "success": True,
                "relation": {
                    "id": f"{created.from_id}-{created.to_id}-{created.relation}",
                    "from_id": created.from_id,
                    "to_id": created.to_id,
                    "relation": created.relation,
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.delete("/api/graph/relation")
    async def delete_relation(
        from_id: str,
        to_id: str,
        relation: str,
        token: str = Depends(verify_token)
    ):
        """
        Delete a relation from the graph.

        Query params:
            from_id: Source entity ID
            to_id: Target entity ID
            relation: Relation type
        """
        try:
            # Create relation object to delete
            rel = Relation(
                from_id=from_id,
                to_id=to_id,
                relation=relation,
            )

            await manager.delete_relations([rel])
            return {"success": True}

        except Exception as e:
            logger.error(f"Error deleting relation: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/graph/entity/{entity_id}/observations")
    async def add_observations(
        entity_id: str,
        observations: List[dict],
        token: str = Depends(verify_token)
    ):
        """
        Add observations to an entity.
        """
        try:
            # Convert to Observation objects
            obs_list = [
                Observation(
                    content=o.get("content", ""),
                    durability=DurabilityType(o.get("durability", "short-term")),
                )
                for o in observations
            ]

            # Create observation request
            request = ObservationRequest(
                entity_id=entity_id,
                observations=obs_list,
            )

            # Apply observations
            results = await manager.apply_observations([request])
            result = results[0]

            if result.errors:
                raise HTTPException(status_code=400, detail=result.errors)

            return {
                "success": True,
                "added_count": len(result.added_observations or [])
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding observations to {entity_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    logger.info("✅ Web API routes configured")
    return app
