import pandas as pd
import asyncio
from app.services.neo4j_service import neo4j_service
from app.logging_utils import ai_logger, db_logger
import os

class ExcelIngestionService:
    async def process_excel(self, file_path: str, folder_id: str):
        """
        Processes an XLSX file, extracts knowledge using Gemini, and ingests into Neo4j.
        """
        if not os.path.exists(file_path):
            ai_logger.error(f"Excel file not found at {file_path}")
            return {"status": "error", "message": "File not found"}

        ai_logger.info(f"Starting Excel Ingestion: {file_path}")
        
        try:
            # Load Excel - Skip highly empty rows and handle unnamed columns
            df = pd.read_excel(file_path)
            
            # Drop rows where everything is NaN
            df = df.dropna(how='all')
            
            # If the first few rows are mostly NaN, they might be headers. 
            # Let's filter for rows that have at least 3 non-NaN values
            df = df[df.notna().sum(axis=1) >= 3]
            
            df = df.reset_index(drop=True)
            ai_logger.info(f"Loaded {len(df)} cleaned rows.")
            
            if df.empty:
                ai_logger.warning("No valid data rows found in Excel after cleaning.")
                return {"status": "error", "message": "No valid data found"}

            # Group rows to avoid too many small LLM calls (Batching)
            batch_size = 5 # Small batch for very dense rows
            total_nodes = 0
            total_rels = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                text_content = batch.to_string(index=False)
                
                ai_logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} rows)")
                # ai_logger.info(f"Batch Text Preview: {text_content[:200]}...")
                
                # Extract using Gemini
                extracted = await gemini_service.extract_scientific_entities(text_content)
                
                ai_logger.info(f"Gemini returned: {len(extracted.get('nodes', []))} nodes, {len(extracted.get('relationships', []))} rels")
                
                nodes = extracted.get("nodes", [])
                relationships = extracted.get("relationships", [])
                
                if nodes or relationships:
                    # Ingest into Neo4j
                    await neo4j_service.merge_entities_with_guardian(nodes, relationships, folder_id)
                    total_nodes += len(nodes)
                    total_rels += len(relationships)
                    ai_logger.info(f"Batch {i//batch_size + 1} ingested: {len(nodes)} nodes, {len(relationships)} rels")
                
            ai_logger.info(f"Excel Ingestion complete. Total: {total_nodes} nodes, {total_rels} rels")
            return {
                "status": "success", 
                "nodes_ingested": total_nodes, 
                "relationships_ingested": total_rels
            }

        except Exception as e:
            ai_logger.error(f"Failed to process Excel: {e}")
            return {"status": "error", "message": str(e)}

excel_service = ExcelIngestionService()
