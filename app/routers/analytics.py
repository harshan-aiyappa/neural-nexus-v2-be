from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from app.services.neo4j_service import neo4j_service
from app.services.gds_service import gds_service
from app.core.security import get_current_user

router = APIRouter()

@router.get("/flow", dependencies=[Depends(get_current_user)])
async def get_flow_data(folder: Optional[str] = None):
    """
    Returns Sankey-compatible flow data by analyzing relationship densities between labels.
    """
    try:
        label_filter = f":Folder_{folder}" if folder else ""
        query = f"""
        MATCH (n{label_filter})-[r]->(m{label_filter})
        WITH labels(n)[0] as source, labels(m)[0] as target, count(r) as value
        WHERE source IS NOT NULL AND target IS NOT NULL
        RETURN source, target, value
        ORDER BY value DESC
        """
        results = await neo4j_service.run_query(query)
        
        # Format for ECharts Sankey
        # ECharts needs unique node names and links referencing them.
        nodes_set = set()
        links = []
        for res in results:
            nodes_set.add(res["source"])
            nodes_set.add(res["target"])
            links.append({
                "source": res["source"],
                "target": res["target"],
                "value": res["value"]
            })
            
        nodes = [{"name": name} for name in nodes_set]
        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", dependencies=[Depends(get_current_user)])
async def get_network_metrics(folder: Optional[str] = None):
    """
    Returns Radar-compatible network metrics using GDS community and influence scores.
    """
    try:
        # Aggregating metrics for the Radar chart
        # 1. Density (proxy: rels/nodes)
        # 2. Influence (proxy: average hub score)
        # 3. Connectivity
        
        # Get basic stats
        label_counts = await neo4j_service.get_label_counts()
        total_nodes = sum(label_counts.values()) or 1
        
        label_filter = f":Folder_{folder}" if folder else ""
        rel_res = await neo4j_service.run_query(f"MATCH (n{label_filter})-[r]->() RETURN count(r) as count")
        total_rels = rel_res[0]["count"] if rel_res else 0
        
        density = (total_rels / total_nodes) * 10 # Scaling for visibility
        
        # Get Pagrank summary
        pagerank = await gds_service.get_pagerank(folder_id=folder)
        avg_influence = sum([p["score"] for p in pagerank[:10]]) / 10 if pagerank else 0
        
        # Community Modularity proxy
        communities = await gds_service.get_communities(folder_id=folder)
        modular_score = (len(communities) / total_nodes) * 100 if total_nodes > 0 else 0

        return {
            "indicators": [
                {"name": "Density", "max": 100},
                {"name": "Influence", "max": 100},
                {"name": "Modularity", "max": 100},
                {"name": "Connectivity", "max": 100},
                {"name": "Reliability", "max": 100}
            ],
            "data": [
                round(float(min(density, 100.0)), 1),
                round(float(min(avg_influence * 5, 100.0)), 1),
                round(float(min(modular_score, 100.0)), 1),
                round(float(min((total_rels / (total_nodes * 2 + 1)) * 100.0, 100.0)), 1),
                99.8 # Base system reliability
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
