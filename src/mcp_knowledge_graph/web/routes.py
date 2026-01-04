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
