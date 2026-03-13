import pandas as pd
import asyncio
from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
from app.logging_utils import ai_logger, db_logger
import os

class ExcelIngestionService:
    async def process_and_ingest(self, df: pd.DataFrame, folder_id: str):
        """
        Processes a pandas DataFrame, extracts knowledge using Gemini, and ingests into Neo4j.
        """
        ai_logger.info(f"Starting Ingestion for DataFrame with {len(df)} rows")
        
        try:
            # Cleaning logic
            df = df.dropna(how='all')
            df = df[df.notna().sum(axis=1) >= 2] # Relaxed to 2 for more extraction
            df = df.reset_index(drop=True)
            
            if df.empty:
                ai_logger.warning("No valid data rows found in DataFrame.")
                return {"status": "error", "message": "No valid data found"}

            batch_size = 5
            total_nodes = 0
            total_rels = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                text_content = batch.to_string(index=False)
                
                ai_logger.info(f"Processing batch {i//batch_size + 1}")
                
                # Extract using Gemini
                extracted = await gemini_service.extract_scientific_entities(text_content)
                
                nodes = extracted.get("nodes", [])
                relationships = extracted.get("relationships", [])
                
                if nodes or relationships:
                    # Ingest into Neo4j with Symmetry Guardian
                    await neo4j_service.merge_entities_with_guardian(nodes, relationships, folder_id)
                    total_nodes += len(nodes)
                    total_rels += len(relationships)
                
            ai_logger.info(f"Ingestion complete. Total: {total_nodes} nodes, {total_rels} rels")
            return {
                "status": "success", 
                "nodes_ingested": total_nodes, 
                "relationships_ingested": total_rels
            }

        except Exception as e:
            ai_logger.error(f"Failed to process DataFrame: {e}")
            return {"status": "error", "message": str(e)}

    async def process_excel(self, file_path: str, folder_id: str):
        """Wrapper for file-based ingestion."""
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File not found"}
        df = pd.read_excel(file_path)
        return await self.process_and_ingest(df, folder_id)

excel_service = ExcelIngestionService()
