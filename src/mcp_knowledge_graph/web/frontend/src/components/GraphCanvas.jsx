import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';

// Register cola layout
cytoscape.use(cola);

const GraphCanvas = ({ graphData, onNodeClick, onEdgeClick, layout = 'cola', filters }) => {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Transform data for Cytoscape
    const elements = [
      // Nodes
      ...graphData.nodes.map(node => ({
        data: {
          id: node.id,
          label: node.name,
          ...node,
        },
        classes: node.entity_type,
      })),
      // Edges
      ...graphData.edges.map(edge => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relation,
          ...edge,
        },
      })),
    ];

    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#60a5fa',
            'color': '#fff',
            'font-size': '12px',
            'width': (node) => Math.max(30, 15 + (node.data('observation_count') || 0) * 2),
            'height': (node) => Math.max(30, 15 + (node.data('observation_count') || 0) * 2),
          }
        },
        {
          selector: 'node.person',
          style: { 'background-color': '#60a5fa' }
        },
        {
          selector: 'node.organization',
          style: { 'background-color': '#f472b6' }
        },
        {
          selector: 'node.event',
          style: { 'background-color': '#34d399' }
        },
        {
          selector: 'node.concept',
          style: { 'background-color': '#a78bfa' }
        },
        {
          selector: 'node.project',
          style: { 'background-color': '#f59e0b' }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#fff',
            'background-color': '#3b82f6',
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'color': '#cbd5e1',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#3b82f6',
            'target-arrow-color': '#3b82f6',
            'width': 3,
          }
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.2,
          }
        },
      ],
      layout: {
        name: layout,
        animate: true,
        nodeDimensionsIncludeLabels: true,
        ...(layout === 'cola' && {
          flow: { axis: 'x', minSeparation: 100 },
          edgeLength: 150,
          nodeSpacing: 50,
        }),
      },
    });

    // Event handlers
    cy.on('tap', 'node', (evt) => {
      onNodeClick?.(evt.target.data());
    });

    cy.on('tap', 'edge', (evt) => {
      onEdgeClick?.(evt.target.data());
    });

    // Click on background to deselect
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        onNodeClick?.(null);
        onEdgeClick?.(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, layout]);

  // Apply filters
  useEffect(() => {
    if (!cyRef.current || !filters) return;

    const cy = cyRef.current;

    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      cy.elements().forEach(ele => {
        const data = ele.data();
        const matches =
          data.label?.toLowerCase().includes(query) ||
          data.entity_type?.toLowerCase().includes(query) ||
          data.name?.toLowerCase().includes(query) ||
          data.relation?.toLowerCase().includes(query) ||
          data.observations?.some(o => o.content.toLowerCase().includes(query));

        if (matches) {
          ele.removeClass('dimmed');
        } else {
          ele.addClass('dimmed');
        }
      });
    } else {
      cy.elements().removeClass('dimmed');
    }

    // Filter by entity type
    if (filters.entityTypes && filters.entityTypes.length > 0) {
      cy.nodes().forEach(node => {
        if (!filters.entityTypes.includes(node.data('entity_type'))) {
          node.addClass('dimmed');
        }
      });
    }
  }, [filters]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#0f172a',
      }}
    />
  );
};

export default GraphCanvas;
