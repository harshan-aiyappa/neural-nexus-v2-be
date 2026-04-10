import asyncio
import httpx
import json

async def verify_neighbors():
    # Use the same base URL as test_features.py but with /api prefix if required
    # Based on graph.py/folders.py being routers, they usually get prefixed in main.py
    # Let's verify if /api/folders or /folders is correct. 
    # test_features.py uses /folders.
    base_url = "http://10.10.20.144:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Try to get folders. Let's try both /api/folders and /folders if first fails.
            print("Step 1: Fetching folders...")
            folders_resp = await client.get(f"{base_url}/api/folders/")
            if folders_resp.status_code != 200:
                 folders_resp = await client.get(f"{base_url}/folders/")
                 
            if folders_resp.status_code != 200:
                print(f"Failed to fetch folders. Status: {folders_resp.status_code}")
                return
            
            folders = folders_resp.json()
            if not folders:
                print("No folders found.")
                return
            
            folder_slug = folders[0]['slug']
            print(f"Using folder slug: {folder_slug}")

            # 2. Get full graph
            print("Step 2: Fetching full graph...")
            graph_url = f"{base_url}/api/graph/full?folder={folder_slug}"
            graph_resp = await client.get(graph_url)
            if graph_resp.status_code != 200:
                graph_url = f"{base_url}/graph/full?folder={folder_slug}"
                graph_resp = await client.get(graph_url)

            if graph_resp.status_code != 200:
                print(f"Failed to fetch graph. Status: {graph_resp.status_code}")
                return

            graph_data = graph_resp.json()
            nodes = graph_data.get('nodes', [])
            if not nodes:
                print("No nodes found in graph.")
                return
            
            test_node = nodes[0]
            node_id = test_node['id']
            print(f"Step 3: Testing neighbors for node: {test_node.get('name')} (ID: {node_id})")

            # 3. Test /neighbors endpoint
            neighbors_url = f"{base_url}/api/graph/neighbors?node_id={node_id}&folder={folder_slug}"
            neighbors_resp = await client.get(neighbors_url)
            if neighbors_resp.status_code != 200:
                neighbors_url = f"{base_url}/graph/neighbors?node_id={node_id}&folder={folder_slug}"
                neighbors_resp = await client.get(neighbors_url)
            
            if neighbors_resp.status_code == 200:
                data = neighbors_resp.json()
                print(f"SUCCESS: Found {len(data.get('nodes', []))} nodes and {len(data.get('relationships', []))} associations.")
                if data.get('nodes'):
                    print("Sample neighbor node:")
                    print(json.dumps(data.get('nodes')[0], indent=2))
            else:
                print(f"FAILED: Neighbors status {neighbors_resp.status_code}")
                print(neighbors_resp.text)

        except Exception as e:
            import traceback
            print(f"Verification script error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_neighbors())
