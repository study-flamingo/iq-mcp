from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_graph(input_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load nodes and edges from a JSONL file.

    Expected input lines:
      {"type": "entity", "data": {"name": str, "entity_type": str, "observations": list[str|{content:str}] , "aliases": list[str]}}
      {"type": "relation", "data": {"from": str, "to": str, "relation": str}}
    """
    nodes_by_id: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON line: {e}\nLine: {line[:200]}")

            typ = obj.get("type")
            data = obj.get("data", {})
            if typ == "entity":
                name = data.get("name")
                if not name:
                    # Skip malformed entity without a name
                    continue
                entity_type = data.get("entity_type", "entity")
                raw_observations = data.get("observations", []) or []
                observations: List[str] = []
                for obs in raw_observations:
                    if isinstance(obs, str):
                        observations.append(obs)
                    elif isinstance(obs, dict):
                        content = obs.get("content") or obs.get("contents")
                        if content:
                            observations.append(str(content))
                aliases = data.get("aliases", []) or []
                node = nodes_by_id.get(name)
                if node is None:
                    node = {
                        "id": name,
                        "entity_type": entity_type,
                        "observations": [],
                        "aliases": aliases,
                    }
                    nodes_by_id[name] = node
                else:
                    # Merge updates if duplicate entity lines appear
                    node["entity_type"] = node.get("entity_type") or entity_type
                    node_aliases = set(node.get("aliases", []))
                    for a in aliases:
                        if a not in node_aliases:
                            node_aliases.add(a)
                    node["aliases"] = sorted(node_aliases)
                # Extend observations without duplicates
                existing_obs = set(node.get("observations", []))
                for o in observations:
                    if o not in existing_obs:
                        existing_obs.add(o)
                node["observations"] = sorted(existing_obs)
            elif typ == "relation":
                src = data.get("from")
                dst = data.get("to")
                rel_type = data.get("relation", "related_to")
                if not src or not dst:
                    continue
                edges.append({"source": src, "target": dst, "relation": rel_type})
            else:
                # Ignore other types for now
                continue

    # Ensure every node referenced by an edge exists at least as a minimal node
    for e in edges:
        for node_id in (e["source"], e["target"]):
            if node_id not in nodes_by_id:
                nodes_by_id[node_id] = {
                    "id": node_id,
                    "entity_type": "entity",
                    "observations": [],
                    "aliases": [],
                }

    nodes = list(nodes_by_id.values())
    return nodes, edges


def _build_html(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], title: str) -> str:
    data_json = json.dumps({"nodes": nodes, "links": edges})

    # Use placeholders to avoid f-string/template literal conflicts.
    html_template = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>[[TITLE]]</title>
    <style>
      :root {
        --bg: #0f172a;         /* slate-900 */
        --panel: #111827;      /* gray-900 */
        --text: #e5e7eb;       /* gray-200 */
        --muted: #94a3b8;      /* slate-400 */
        --accent: #60a5fa;     /* blue-400 */
        --accent-2: #f472b6;   /* pink-400 */
        --accent-3: #34d399;   /* emerald-400 */
        --edge: #475569;       /* slate-600 */
      }
      * { box-sizing: border-box; }
      body { margin: 0; background: var(--bg); color: var(--text); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, Noto Sans, Apple Color Emoji, Segoe UI Emoji; }
      .layout { display: grid; grid-template-columns: 1fr 340px; gap: 0; height: 100vh; }
      .toolbar { position: sticky; top: 0; display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: rgba(2,6,23,0.7); backdrop-filter: blur(6px); border-bottom: 1px solid #1f2937; z-index: 5; }
      .toolbar input { width: 360px; max-width: 50vw; padding: 8px 10px; border-radius: 8px; border: 1px solid #374151; background: #0b1220; color: var(--text); }
      #graph { width: 100%; height: calc(100vh - 50px); }
      .panel { border-left: 1px solid #1f2937; background: var(--panel); padding: 12px 14px; overflow: auto; }
      .panel h2 { margin: 6px 0 10px; font-size: 18px; }
      .panel .muted { color: var(--muted); font-size: 12px; }
      .chip { display: inline-block; padding: 2px 8px; border-radius: 9999px; background: #0b1220; border: 1px solid #1f2937; color: var(--muted); font-size: 11px; margin-right: 6px; }
      ul { padding-left: 16px; }
      li { margin: 4px 0; }
      .legend { display: flex; gap: 12px; align-items: center; color: var(--muted); font-size: 12px; }
      .legend .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-right: 6px; }

      /* Graph styles */
      .link { stroke: var(--edge); stroke-opacity: 0.6; }
      .link-label { font-size: 10px; fill: #cbd5e1; pointer-events: none; }
      .node circle { stroke: #0b1220; stroke-width: 1.5px; }
      .node text { font-size: 11px; fill: #e2e8f0; pointer-events: none; }
      .node.hover circle { stroke: #ffffff; stroke-width: 2px; }
      .node.dimmed { opacity: 0.25; }
      .link.dimmed { opacity: 0.15; }
    </style>
  </head>
  <body>
    <div class="toolbar">
      <input id="search" type="text" placeholder="Search nodes and observations..." />
      <div class="legend"></div>
    </div>
    <div class="layout">
      <div id="graph"></div>
      <aside class="panel">
        <h2 id="panel-title">Select a node</h2>
        <div class="muted" id="panel-sub">Click a node to view details</div>
        <div id="panel-content"></div>
      </aside>
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
      const data = [[DATA_JSON]];

      // Build color palette from entity types
      const typeSet = Array.from(new Set(data.nodes.map(n => n.entity_type || 'entity'))).sort();
      const color = d3.scaleOrdinal()
        .domain(typeSet)
        .range(['#60a5fa','#f472b6','#34d399','#f59e0b','#a78bfa','#f87171','#22d3ee','#84cc16','#eab308','#fb7185']);

      // Legend
      const legend = d3.select('.legend');
      typeSet.forEach(t => {
        const item = legend.append('div').style('display','flex').style('align-items','center');
        item.append('span').attr('class','swatch').style('background', color(t));
        item.append('span').text(t);
      });

      // Setup SVG
      const container = d3.select('#graph');
      const width = container.node().clientWidth;
      const height = container.node().clientHeight;

      const svg = container.append('svg')
        .attr('width', width)
        .attr('height', height);

      const zoomLayer = svg.append('g');

      // Define markers for directed edges
      svg.append('defs').selectAll('marker')
        .data(['arrow'])
        .enter()
        .append('marker')
          .attr('id', d => d)
          .attr('viewBox', '0 -5 10 10')
          .attr('refX', 16)
          .attr('refY', 0)
          .attr('markerWidth', 6)
          .attr('markerHeight', 6)
          .attr('orient', 'auto')
        .append('path')
          .attr('d', 'M0,-5L10,0L0,5')
          .attr('fill', '#64748b');

      // Simulation
      const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(30));

      // Links
      const link = zoomLayer.append('g')
        .attr('stroke-width', 1.4)
        .selectAll('line')
        .data(data.links)
        .join('line')
        .attr('class', 'link')
        .attr('marker-end', 'url(#arrow)');

      // Link labels
      const linkLabels = zoomLayer.append('g')
        .selectAll('text')
        .data(data.links)
        .join('text')
        .attr('class', 'link-label')
        .text(d => d.relation || 'related_to');

      // Nodes
      const node = zoomLayer.append('g')
        .selectAll('g')
        .data(data.nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));

      node.append('circle')
        .attr('r', d => 10 + Math.min(10, (d.observations?.length || 0)))
        .attr('fill', d => color(d.entity_type || 'entity'));

      node.append('text')
        .attr('x', 14)
        .attr('y', 4)
        .text(d => d.id);

      node.on('click', (event, d) => {
        selectNode(d);
        event.stopPropagation();
      });

      svg.on('click', () => selectNode(null));

      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);

        // Position labels midway along the link
        linkLabels
          .attr('x', d => (d.source.x + d.target.x) / 2)
          .attr('y', d => (d.source.y + d.target.y) / 2 - 4);

        node
          .attr('transform', d => `translate(${d.x},${d.y})`);
      });

      // Zoom / pan
      svg.call(d3.zoom().on('zoom', ({transform}) => {
        zoomLayer.attr('transform', transform);
      }));

      // Search/filter
      const search = document.getElementById('search');
      search.addEventListener('input', () => {
        const q = search.value.trim().toLowerCase();
        if (!q) {
          node.classed('dimmed', false);
          link.classed('dimmed', false);
          return;
        }
        const matchesNode = (n) => {
          if (n.id.toLowerCase().includes(q)) return true;
          if ((n.entity_type || '').toLowerCase().includes(q)) return true;
          if ((n.aliases || []).some(a => a.toLowerCase().includes(q))) return true;
          if ((n.observations || []).some(o => (o+"").toLowerCase().includes(q))) return true;
          return false;
        };
        const matchedIds = new Set(data.nodes.filter(matchesNode).map(n => n.id));
        node.classed('dimmed', d => !matchedIds.has(d.id));
        link.classed('dimmed', d => !(matchedIds.has(d.source.id) || matchedIds.has(d.target.id)));
      });

      function selectNode(d) {
        const title = document.getElementById('panel-title');
        const sub = document.getElementById('panel-sub');
        const content = document.getElementById('panel-content');
        d3.selectAll('.node').classed('hover', n => d && n.id === d.id);
        if (!d) {
          title.textContent = 'Select a node';
          sub.textContent = 'Click a node to view details';
          content.innerHTML = '';
          return;
        }
        title.textContent = d.id;
        sub.innerHTML = '';
        const chips = [];
        if (d.entity_type) chips.push(`<span class="chip">${d.entity_type}</span>`);
        if (d.aliases && d.aliases.length) chips.push(`<span class="chip">aliases: ${d.aliases.join(', ')}</span>`);
        if (chips.length) content.innerHTML = chips.join(' ');
        else content.innerHTML = '';

        const obs = d.observations || [];
        if (obs.length) {
          const list = document.createElement('ul');
          obs.forEach(o => {
            const li = document.createElement('li');
            li.textContent = o;
            list.appendChild(li);
          });
          const h = document.createElement('h3');
          h.textContent = `Observations (${obs.length})`;
          content.appendChild(h);
          content.appendChild(list);
        }

        // Highlight neighbors
        const neighbors = new Set([d.id]);
        data.links.forEach(l => {
          if (l.source.id === d.id) neighbors.add(l.target.id);
          if (l.target.id === d.id) neighbors.add(l.source.id);
        });
        node.classed('dimmed', n => !neighbors.has(n.id));
        link.classed('dimmed', l => !(neighbors.has(l.source.id) && neighbors.has(l.target.id)));
      }

      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      }
      function dragged(event, d) {
        d.fx = event.x; d.fy = event.y;
      }
      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      }
    </script>
  </body>
</html>
"""
    return html_template.replace("[[DATA_JSON]]", data_json).replace("[[TITLE]]", title)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a simple HTML visualization of a knowledge graph JSONL file.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to input JSONL (e.g., example.json)")
    parser.add_argument("--output", "-o", type=Path, default=Path("graph.html"), help="Path to output HTML file")
    parser.add_argument("--title", "-t", type=str, default="Knowledge Graph", help="Page title")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2

    nodes, edges = _load_graph(args.input)
    html = _build_html(nodes, edges, args.title)

    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote visualization to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
