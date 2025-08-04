#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Parse command line arguments
function parseArgs(): { memoryPath?: string } {
    const args = process.argv.slice(2);
    const result: { memoryPath?: string } = {};
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--memory-path' && i + 1 < args.length) {
            result.memoryPath = args[i + 1];
            i++; // Skip next argument since we consumed it
        }
    }
    
    return result;
}

// Define memory file path with multiple sources (CLI args > env var > default)
const defaultMemoryPath = path.join(path.dirname(fileURLToPath(import.meta.url)), 'memory.json');
const cliArgs = parseArgs();

const MEMORY_FILE_PATH = cliArgs.memoryPath 
    ? path.isAbsolute(cliArgs.memoryPath)
        ? cliArgs.memoryPath
        : path.join(path.dirname(fileURLToPath(import.meta.url)), cliArgs.memoryPath)
    : process.env.MEMORY_FILE_PATH
        ? path.isAbsolute(process.env.MEMORY_FILE_PATH)
            ? process.env.MEMORY_FILE_PATH
            : path.join(path.dirname(fileURLToPath(import.meta.url)), process.env.MEMORY_FILE_PATH)
        : defaultMemoryPath;
        
// NEW: Enhanced observation structure
interface TimestampedObservation {
  content: string;
  timestamp: string; // ISO date string
  durability: 'permanent' | 'long-term' | 'short-term' | 'temporary'; // String literal type
}

// NEW: Helper type for creating observations - makes durability optional
interface ObservationInput {
  content: string;
  durability?: 'permanent' | 'long-term' | 'short-term' | 'temporary';
}

// UPDATED: Entity interface now supports both old and new observation formats
interface Entity {
  name: string;
  entityType: string;
  observations: (string | TimestampedObservation)[]; // Union type for backward compatibility
}

// Keep existing interfaces unchanged for backward compatibility
interface Relation {
    from: string;
    to: string;
    relationType: string;
}

interface KnowledgeGraph {
    entities: Entity[];
    relations: Relation[];
}

// The KnowledgeGraphManager class contains all operations to interact with the knowledge graph
class KnowledgeGraphManager {
    // NEW: Helper method to create timestamped observations
    private createTimestampedObservation(input: string | ObservationInput): TimestampedObservation {
        // If it's just a string (old format), convert it
        if (typeof input === 'string') {
            return {
                content: input,
                timestamp: new Date().toISOString(),
                durability: 'long-term' // Default for backward compatibility
            };
        }
        
        // If it's already an ObservationInput object, add timestamp and default durability
        return {
            content: input.content,
            timestamp: new Date().toISOString(),
            durability: input.durability || 'long-term' // Default value using || operator
        };
    }

    // NEW: Helper method to normalize observations (convert old string format to new format)
    private normalizeObservation(obs: string | TimestampedObservation): TimestampedObservation {
        if (typeof obs === 'string') {
            return this.createTimestampedObservation(obs);
        }
        return obs;
    }

    // NEW: Method to check if an observation is likely outdated
    private isObservationOutdated(obs: TimestampedObservation): boolean {
        const now = new Date();
        const obsDate = new Date(obs.timestamp);
        const monthsOld = (now.getTime() - obsDate.getTime()) / (1000 * 60 * 60 * 24 * 30);
        
        switch (obs.durability) {
            case 'permanent':
                return false; // Never outdated
            case 'long-term':
                return monthsOld > 24; // 2+ years old
            case 'short-term':
                return monthsOld > 6; // 6+ months old
            case 'temporary':
                return monthsOld > 1; // 1+ month old
            default:
                return false;
        }
    }

    private async loadGraph(): Promise<KnowledgeGraph> {
        try {
            const data = await fs.readFile(MEMORY_FILE_PATH, "utf-8");
            const lines = data.split("\n").filter(line => line.trim() !== "");
            const graph = lines.reduce((graph: KnowledgeGraph, line) => {
                const item = JSON.parse(line);
                if (item.type === "entity") {
                    // NEW: Normalize observations when loading
                    const entity = item as Entity;
                    entity.observations = entity.observations.map(obs => this.normalizeObservation(obs));
                    graph.entities.push(entity);
                }
                if (item.type === "relation") graph.relations.push(item as Relation);
                return graph;
            }, { entities: [], relations: [] });
            
            return graph;
        } catch (error) {
            if (error instanceof Error && 'code' in error && (error as any).code === "ENOENT") {
                return { entities: [], relations: [] };
            }
            throw error;
        }
    }

    private async saveGraph(graph: KnowledgeGraph): Promise<void> {
        const lines = [
            ...graph.entities.map(e => JSON.stringify({ type: "entity", ...e })),
            ...graph.relations.map(r => JSON.stringify({ type: "relation", ...r })),
        ];
        await fs.writeFile(MEMORY_FILE_PATH, lines.join("\n"));
    }

    async createEntities(entities: Entity[]): Promise<Entity[]> {
        const graph = await this.loadGraph();
        const newEntities = entities.filter(e => !graph.entities.some(existingEntity => existingEntity.name === e.name));
        graph.entities.push(...newEntities);
        await this.saveGraph(graph);
        return newEntities;
    }

    async createRelations(relations: Relation[]): Promise<Relation[]> {
        const graph = await this.loadGraph();
        const newRelations = relations.filter(r => !graph.relations.some(existingRelation =>
            existingRelation.from === r.from &&
            existingRelation.to === r.to &&
            existingRelation.relationType === r.relationType
        ));
        graph.relations.push(...newRelations);
        await this.saveGraph(graph);
        return newRelations;
    }

    // UPDATED: Enhanced method to add observations with temporal data
    async addObservations(observations: {
        entityName: string;
        contents: (string | ObservationInput)[]
    }[]): Promise<{
        entityName: string;
        addedObservations: TimestampedObservation[]
    }[]> {
        const graph = await this.loadGraph();
        
        const results = observations.map(o => {
            const entity = graph.entities.find(e => e.name === o.entityName);
            if (!entity) {
                throw new Error(`Entity with name ${o.entityName} not found`);
            }
            
            // Convert all observations to TimestampedObservation format
            const newTimestampedObs = o.contents.map(content => this.createTimestampedObservation(content));
            
            // Check for duplicates by content (not by full object)
            const existingContents = entity.observations.map(obs =>
                typeof obs === 'string' ? obs : obs.content
            );
            
            const uniqueNewObs = newTimestampedObs.filter(newObs =>
                !existingContents.includes(newObs.content)
            );
            
            // Add new observations
            entity.observations.push(...uniqueNewObs);
            
            return {
                entityName: o.entityName,
                addedObservations: uniqueNewObs
            };
        });
        
        await this.saveGraph(graph);
        return results;
    }

    // NEW: Method to clean up outdated observations
    async cleanupOutdatedObservations(): Promise<{
        entitiesProcessed: number;
        observationsRemoved: number;
        removedObservations: { entityName: string; content: string; age: string }[];
    }> {
        const graph = await this.loadGraph();
        let totalRemoved = 0;
        const removedDetails: { entityName: string; content: string; age: string }[] = [];
        
        for (const entity of graph.entities) {
            const originalCount = entity.observations.length;
            
            // Normalize all observations first
            const normalizedObs = entity.observations.map(obs => this.normalizeObservation(obs));
            
            // Filter out outdated observations
            entity.observations = normalizedObs.filter(obs => {
                const isOutdated = this.isObservationOutdated(obs);
                if (isOutdated) {
                    const age = Math.round(
                        (new Date().getTime() - new Date(obs.timestamp).getTime()) / (1000 * 60 * 60 * 24)
                    );
                    removedDetails.push({
                        entityName: entity.name,
                        content: obs.content,
                        age: `${age} days old`
                    });
                }
                return !isOutdated;
            });
            
            totalRemoved += originalCount - entity.observations.length;
        }
        
        if (totalRemoved > 0) {
            await this.saveGraph(graph);
        }
        
        return {
            entitiesProcessed: graph.entities.length,
            observationsRemoved: totalRemoved,
            removedObservations: removedDetails
        };
    }

    // NEW: Method to get observations by durability
    async getObservationsByDurability(entityName: string): Promise<{
        permanent: TimestampedObservation[];
        longTerm: TimestampedObservation[];
        shortTerm: TimestampedObservation[];
        temporary: TimestampedObservation[];
    }> {
        const graph = await this.loadGraph();
        const entity = graph.entities.find(e => e.name === entityName);
        
        if (!entity) {
            throw new Error(`Entity ${entityName} not found`);
        }
        
        // Normalize all observations
        const normalizedObs = entity.observations.map(obs => this.normalizeObservation(obs));
        
        return {
            permanent: normalizedObs.filter(obs => obs.durability === 'permanent'),
            longTerm: normalizedObs.filter(obs => obs.durability === 'long-term'),
            shortTerm: normalizedObs.filter(obs => obs.durability === 'short-term'),
            temporary: normalizedObs.filter(obs => obs.durability === 'temporary')
        };
    }

    async deleteEntities(entityNames: string[]): Promise<void> {
        const graph = await this.loadGraph();
        graph.entities = graph.entities.filter(e => !entityNames.includes(e.name));
        graph.relations = graph.relations.filter(r => !entityNames.includes(r.from) && !entityNames.includes(r.to));
        await this.saveGraph(graph);
    }

    async deleteObservations(deletions: { entityName: string; observations: string[] }[]): Promise<void> {
        const graph = await this.loadGraph();
        deletions.forEach(d => {
            const entity = graph.entities.find(e => e.name === d.entityName);
            if (entity) {
                entity.observations = entity.observations.filter(o => {
                    const content = typeof o === 'string' ? o : o.content;
                    return !d.observations.includes(content);
                });
            }
        });
        await this.saveGraph(graph);
    }

    async deleteRelations(relations: Relation[]): Promise<void> {
        const graph = await this.loadGraph();
        graph.relations = graph.relations.filter(r => !relations.some(delRelation =>
            r.from === delRelation.from &&
            r.to === delRelation.to &&
            r.relationType === delRelation.relationType
        ));
        await this.saveGraph(graph);
    }

    async readGraph(): Promise<KnowledgeGraph> {
        return this.loadGraph();
    }

    async searchNodes(query: string): Promise<KnowledgeGraph> {
        const graph = await this.loadGraph();

        const filteredEntities = graph.entities.filter(e =>
            e.name.toLowerCase().includes(query.toLowerCase()) ||
            e.entityType.toLowerCase().includes(query.toLowerCase()) ||
            e.observations.some(o => {
                const content = typeof o === 'string' ? o : o.content;
                return content.toLowerCase().includes(query.toLowerCase());
            })
        );

        const filteredEntityNames = new Set(filteredEntities.map(e => e.name));
        const filteredRelations = graph.relations.filter(r =>
            filteredEntityNames.has(r.from) && filteredEntityNames.has(r.to)
        );

        return {
            entities: filteredEntities,
            relations: filteredRelations,
        };
    }

    async openNodes(names: string[]): Promise<KnowledgeGraph> {
        const graph = await this.loadGraph();

        const filteredEntities = graph.entities.filter(e => names.includes(e.name));
        const filteredEntityNames = new Set(filteredEntities.map(e => e.name));
        const filteredRelations = graph.relations.filter(r =>
            filteredEntityNames.has(r.from) && filteredEntityNames.has(r.to)
        );

        return {
            entities: filteredEntities,
            relations: filteredRelations,
        };
    }
}

const knowledgeGraphManager = new KnowledgeGraphManager();

// The server instance and tools exposed to Claude
const server = new Server({
    name: "memory-server",
    version: "0.7.0", // Bumped version for temporal features
}, {
    capabilities: {
        tools: {},
    },
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "create_entities",
                description: "Create multiple new entities in the knowledge graph",
                inputSchema: {
                    type: "object",
                    properties: {
                        entities: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    name: { type: "string", description: "The name of the entity" },
                                    entityType: { type: "string", description: "The type of the entity" },
                                    observations: {
                                        type: "array",
                                        items: { type: "string" },
                                        description: "An array of observation contents associated with the entity"
                                    },
                                },
                                required: ["name", "entityType", "observations"],
                            },
                        },
                    },
                    required: ["entities"],
                },
            },
            {
                name: "create_relations",
                description: "Create multiple new relations between entities in the knowledge graph. Relations should be in active voice",
                inputSchema: {
                    type: "object",
                    properties: {
                        relations: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    from: { type: "string", description: "The name of the entity where the relation starts" },
                                    to: { type: "string", description: "The name of the entity where the relation ends" },
                                    relationType: { type: "string", description: "The type of the relation" },
                                },
                                required: ["from", "to", "relationType"],
                            },
                        },
                    },
                    required: ["relations"],
                },
            },
            {
                name: "add_observations",
                description: "Add new observations to existing entities in the knowledge graph. Supports both simple strings and temporal observations with durability metadata (permanent, long-term, short-term, temporary)",
                inputSchema: {
                    type: "object",
                    properties: {
                        observations: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    entityName: { type: "string", description: "The name of the entity to add observations to" },
                                    contents: {
                                        type: "array",
                                        items: {
                                            oneOf: [
                                                { type: "string" }, // Simple string observation (defaults to long-term)
                                                {
                                                    type: "object",
                                                    properties: {
                                                        content: { type: "string", description: "The observation content" },
                                                        durability: {
                                                            type: "string",
                                                            enum: ["permanent", "long-term", "short-term", "temporary"],
                                                            description: "How long this observation is expected to remain relevant"
                                                        }
                                                    },
                                                    required: ["content"]
                                                }
                                            ]
                                        },
                                        description: "Observations to add - can be simple strings or objects with durability metadata"
                                    },
                                },
                                required: ["entityName", "contents"],
                            },
                        },
                    },
                    required: ["observations"],
                },
            },
            {
                name: "cleanup_outdated_observations",
                description: "Remove observations that are likely outdated based on their durability and age",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "get_observations_by_durability",
                description: "Get observations for an entity grouped by their durability type",
                inputSchema: {
                    type: "object",
                    properties: {
                        entityName: { type: "string", description: "The name of the entity to get observations for" },
                    },
                    required: ["entityName"],
                },
            },
            {
                name: "delete_entities",
                description: "Delete multiple entities and their associated relations from the knowledge graph",
                inputSchema: {
                    type: "object",
                    properties: {
                        entityNames: {
                            type: "array",
                            items: { type: "string" },
                            description: "An array of entity names to delete"
                        },
                    },
                    required: ["entityNames"],
                },
            },
            {
                name: "delete_observations",
                description: "Delete specific observations from entities in the knowledge graph",
                inputSchema: {
                    type: "object",
                    properties: {
                        deletions: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    entityName: { type: "string", description: "The name of the entity containing the observations" },
                                    observations: {
                                        type: "array",
                                        items: { type: "string" },
                                        description: "An array of observations to delete"
                                    },
                                },
                                required: ["entityName", "observations"],
                            },
                        },
                    },
                    required: ["deletions"],
                },
            },
            {
                name: "delete_relations",
                description: "Delete multiple relations from the knowledge graph",
                inputSchema: {
                    type: "object",
                    properties: {
                        relations: {
                            type: "array",
                            items: {
                                type: "object",
                                properties: {
                                    from: { type: "string", description: "The name of the entity where the relation starts" },
                                    to: { type: "string", description: "The name of the entity where the relation ends" },
                                    relationType: { type: "string", description: "The type of the relation" },
                                },
                                required: ["from", "to", "relationType"],
                            },
                            description: "An array of relations to delete"
                        },
                    },
                    required: ["relations"],
                },
            },
            {
                name: "read_graph",
                description: "Read the entire knowledge graph",
                inputSchema: {
                    type: "object",
                    properties: {},
                },
            },
            {
                name: "search_nodes",
                description: "Search for nodes in the knowledge graph based on a query",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The search query to match against entity names, types, and observation content" },
                    },
                    required: ["query"],
                },
            },
            {
                name: "open_nodes",
                description: "Open specific nodes in the knowledge graph by their names",
                inputSchema: {
                    type: "object",
                    properties: {
                        names: {
                            type: "array",
                            items: { type: "string" },
                            description: "An array of entity names to retrieve",
                        },
                    },
                    required: ["names"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    if (!args) {
        throw new Error(`No arguments provided for tool: ${name}`);
    }

    try {
        switch (name) {
            case "create_entities":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.createEntities(args.entities as Entity[]), null, 2) }] };
            case "create_relations":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.createRelations(args.relations as Relation[]), null, 2) }] };
            case "add_observations":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.addObservations(args.observations as { entityName: string; contents: (string | ObservationInput)[] }[]), null, 2) }] };
            case "cleanup_outdated_observations":
                const cleanupResult = await knowledgeGraphManager.cleanupOutdatedObservations();
                return {
                    content: [{
                        type: "text",
                        text: JSON.stringify(cleanupResult, null, 2)
                    }]
                };
            case "get_observations_by_durability":
                const durabilityResult = await knowledgeGraphManager.getObservationsByDurability(args.entityName as string);
                return {
                    content: [{
                        type: "text",
                        text: JSON.stringify(durabilityResult, null, 2)
                    }]
                };
            case "delete_entities":
                await knowledgeGraphManager.deleteEntities(args.entityNames as string[]);
                return { content: [{ type: "text", text: "Entities deleted successfully" }] };
            case "delete_observations":
                await knowledgeGraphManager.deleteObservations(args.deletions as { entityName: string; observations: string[] }[]);
                return { content: [{ type: "text", text: "Observations deleted successfully" }] };
            case "delete_relations":
                await knowledgeGraphManager.deleteRelations(args.relations as Relation[]);
                return { content: [{ type: "text", text: "Relations deleted successfully" }] };
            case "read_graph":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.readGraph(), null, 2) }] };
            case "search_nodes":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.searchNodes(args.query as string), null, 2) }] };
            case "open_nodes":
                return { content: [{ type: "text", text: JSON.stringify(await knowledgeGraphManager.openNodes(args.names as string[]), null, 2) }] };
            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    } catch (error) {
        console.error(`Error in tool ${name}:`, error);
        return {
            content: [{
                type: "text",
                text: JSON.stringify({
                    error: error instanceof Error ? error.message : "Unknown error",
                    tool: name
                }, null, 2)
            }],
            isError: true
        };
    }
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Enhanced Knowledge Graph MCP Server with Temporal Observations running on stdio");
}

main().catch((error) => {
    console.error("Fatal error in main():", error);
    process.exit(1);
});
