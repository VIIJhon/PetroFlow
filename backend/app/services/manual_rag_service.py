"""
Technical Manual RAG (Retrieval-Augmented Generation) Service
Handles PDF text extraction using PyPDF2, overlapping chunking, keyword extraction, and offline search index weighting.
"""

import os
import io
import re
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.models.manual import TechnicalManual, ManualChunk

logger = logging.getLogger(__name__)

# List of common Spanish and English stop words to filter key concepts
STOPWORDS = {
    # English
    'the', 'of', 'and', 'to', 'in', 'is', 'for', 'with', 'on', 'at', 'by', 'an', 'be', 'this', 'that', 'from', 'it', 'are', 'as', 'was',
    # Spanish
    'el', 'la', 'los', 'las', 'de', 'y', 'a', 'en', 'es', 'para', 'con', 'un', 'una', 'unos', 'unas', 'del', 'al', 'o', 'por', 'como',
    'su', 'sus', 'este', 'esta', 'se', 'que', 'lo', 'le', 'les', 'nos', 'mi', 'sin', 'sobre', 'tras', 'durante', 'contra', 'entre'
}


class ManualRAGService:
    """Service to ingest PDFs, generate overlapping text chunks, extract keywords, and perform local vector-like searches"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract text from PDF pages using PyPDF2
        """
        try:
            import PyPDF2
            
            pages_text = []
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PyPDF2.PdfReader(pdf_file)
            
            for page_idx in range(len(reader.pages)):
                try:
                    page = reader.pages[page_idx]
                    page_text = page.extract_text() or ""
                    # Basic cleaning
                    page_text = re.sub(r'\s+', ' ', page_text).strip()
                    pages_text.append({
                        "page_number": page_idx + 1,
                        "text": page_text
                    })
                except Exception as page_err:
                    logger.warning(f"Error extracting page {page_idx + 1}: {page_err}")
                    # Keep empty page placeholder to preserve numbering
                    pages_text.append({
                        "page_number": page_idx + 1,
                        "text": ""
                    })
                    
            return pages_text
        except ImportError:
            logger.error("PyPDF2 is not installed!")
            raise ImportError("PyPDF2 no esta instalado. Por favor agreguelo a su entorno virtual.")
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            raise ValueError(f"Error al leer el archivo PDF: {str(e)}")

    @staticmethod
    def chunk_text(pages: List[Dict[str, Any]], chunk_size_words: int = 300, overlap_words: int = 50) -> List[Dict[str, Any]]:
        """
        Split page-by-page text into overlapping chunks of ~300 words with 50 words overlap
        """
        chunks = []
        all_words_with_page = []
        
        # Flatten all words with their respective page numbers
        for page in pages:
            words = page["text"].split(" ")
            for w in words:
                if w.strip():
                    all_words_with_page.append({
                        "word": w,
                        "page_number": page["page_number"]
                    })
                    
        total_words = len(all_words_with_page)
        if total_words == 0:
            return []
            
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < total_words:
            end_idx = min(start_idx + chunk_size_words, total_words)
            chunk_data = all_words_with_page[start_idx:end_idx]
            
            # Reconstruct text
            chunk_text = " ".join([d["word"] for d in chunk_data])
            # Predominant page number for this chunk is the middle word's page
            middle_page = chunk_data[len(chunk_data) // 2]["page_number"]
            
            # Simple keyword extraction for this specific chunk
            keywords = ManualRAGService.extract_keywords(chunk_text)
            
            chunks.append({
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "keywords": keywords,
                "page_number": middle_page,
                "char_start": start_idx,
                "char_end": end_idx
            })
            
            chunk_idx += 1
            # Move index with overlap
            start_idx += (chunk_size_words - overlap_words)
            
            # Break if we reached end
            if start_idx >= total_words - overlap_words:
                break
                
        return chunks

    @staticmethod
    def extract_keywords(text: str, top_n: int = 15) -> List[str]:
        """
        Simple, dependency-free Spanish/English keyword extraction from text
        """
        # Lowercase and clean punctuation
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        words = cleaned.split()
        
        # Count term frequencies, skipping short terms and stop words
        freqs = {}
        for word in words:
            if len(word) > 3 and word not in STOPWORDS and not word.isdigit():
                freqs[word] = freqs.get(word, 0) + 1
                
        # Sort by frequency
        sorted_freqs = sorted(freqs.items(), key=lambda item: item[1], reverse=True)
        return [w for w, _ in sorted_freqs[:top_n]]

    @staticmethod
    def compute_match_score(query: str, chunk_keywords: List[str], chunk_text: str) -> float:
        """
        Calculate local similarity score (0.0 - 1.0) between query and chunk
        """
        query_words = re.sub(r'[^\w\s]', '', query.lower()).split()
        query_words = [w for w in query_words if w not in STOPWORDS]
        
        if not query_words:
            return 0.0
            
        score = 0.0
        text_lower = chunk_text.lower()
        
        for q_word in query_words:
            # Term matches key list (high weight)
            if q_word in chunk_keywords:
                score += 2.0
            # Term is inside text body (lower weight)
            elif q_word in text_lower:
                # Count frequency of query word in chunk text
                count = text_lower.count(q_word)
                score += min(1.0, count * 0.2)
                
        # Normalize by query length
        return min(1.0, score / (len(query_words) * 2.0))

    @staticmethod
    def search_manuals(
        query: str,
        top_k: int = 5,
        norm_filter: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Search manuals offline using local tf-idf style cosine / keyword scoring
        """
        if not db:
            from app.database import SessionLocal
            db = SessionLocal()
            close_session = True
        else:
            close_session = False
            
        try:
            # Get all manual chunks, joined with their respective manual headers
            query_db = db.query(ManualChunk, TechnicalManual).join(
                TechnicalManual, ManualChunk.manual_id == TechnicalManual.id
            )
            
            # Filter by norm if supplied
            if norm_filter:
                query_db = query_db.filter(TechnicalManual.norm_standard == norm_filter)
                
            # Keep limit reasonable to prevent memory blow up on huge SQLite databases
            # Get all chunks to score locally (we usually have 500-5000 chunks max in an industrial offline app)
            all_rows = query_db.all()
            
            scored_chunks = []
            for chunk, manual in all_rows:
                # Ensure correct keyword type
                keywords_list = chunk.keywords
                if isinstance(keywords_list, str):
                    try:
                        keywords_list = json.loads(keywords_list)
                    except ValueError:
                        keywords_list = []
                        
                score = ManualRAGService.compute_match_score(query, keywords_list or [], chunk.text)
                
                if score > 0.05:  # Relevance threshold
                    scored_chunks.append({
                        "manual_id": manual.id,
                        "title": manual.title,
                        "norm_standard": manual.norm_standard,
                        "equipment_type": manual.equipment_type,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                        "score": round(score, 4)
                    })
                    
            # Sort by score descending
            scored_chunks.sort(key=lambda item: item["score"], reverse=True)
            return scored_chunks[:top_k]
            
        finally:
            if close_session:
                db.close()

    @staticmethod
    def index_manual_document(manual_id: int, file_content: bytes, db: Session) -> None:
        """
        Synchronous / background indexing task for uploaded manual PDF documents
        """
        manual = db.query(TechnicalManual).filter(TechnicalManual.id == manual_id).first()
        if not manual:
            return
            
        try:
            # Step 1: Extract page by page text
            pages = ManualRAGService.extract_text_from_pdf(file_content)
            
            # Step 2: Generate overlapping chunks
            chunks = ManualRAGService.chunk_text(pages)
            
            if not chunks:
                raise ValueError("No se pudo extraer texto del PDF (documento vacio o escaneado sin OCR)")
                
            # Step 3: Insert chunks to database
            for chunk in chunks:
                db_chunk = ManualChunk(
                    manual_id=manual_id,
                    chunk_index=chunk["chunk_index"],
                    text=chunk["text"],
                    keywords=chunk["keywords"],
                    page_number=chunk["page_number"],
                    char_start=chunk["char_start"],
                    char_end=chunk["char_end"]
                )
                db.add(db_chunk)
                
            # Step 4: Complete header status
            manual.total_chunks = len(chunks)
            manual.status = "ready"
            manual.error_message = None
            db.commit()
            logger.info(f"Manual ID {manual_id} successfully indexed with {len(chunks)} chunks.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error indexing manual ID {manual_id}: {e}")
            manual.status = "error"
            manual.error_message = str(e)
            db.commit()
