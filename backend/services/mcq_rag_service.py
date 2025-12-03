"""
RAG System Implementation with ChromaDB
Handles vector store initialization and question retrieval
"""
import json
import os
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class RAGSystem:
    """Manages ChromaDB vector store and question retrieval"""
    
    def __init__(self, questions_path: str = "utils/mcq/questions.json", db_path: str = "utils/mcq/chroma_db"):
        """
        Initialize RAG system
        
        Args:
            questions_path: Path to questions.json file
            db_path: Path to ChromaDB storage directory
        """
        self.questions_path = questions_path
        self.db_path = db_path
        self.embedding_model = None
        self.client = None
        self.collection = None
        self._initialized = False
    
    def _load_embedding_model(self):
        """Load sentence-transformers model"""
        if self.embedding_model is None:
            # Use all-mpnet-base-v2 for high quality (768-dim)
            # Alternative: all-MiniLM-L6-v2 for faster (384-dim)
            self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
    
    def _determine_domain(self, question_id: str) -> str:
        """
        Determine domain based on question ID
        
        Args:
            question_id: Question ID like "Q001", "Q150", etc.
            
        Returns:
            Domain name
        """
        # Extract number from question_id (e.g., "Q001" -> 1)
        try:
            q_num = int(question_id[1:])
        except (ValueError, IndexError):
            return "unknown"
        
        if 1 <= q_num <= 150:
            return "genAI"
        elif 151 <= q_num <= 300:
            return "java"
        elif 301 <= q_num <= 420:
            return "python_backend"
        elif 421 <= q_num <= 570:
            return "java_backend"
        elif q_num >= 571:
            return "cloud"
        else:
            return "unknown"
    
    def _create_embedding_text(self, question: Dict[str, Any]) -> str:
        """
        Create text for embedding: question + tags
        
        Args:
            question: Question dictionary
            
        Returns:
            Combined text for embedding
        """
        question_text = question.get("question", "")
        tags = question.get("tags", [])
        tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)
        
        # Combine question and tags
        embedding_text = f"{question_text} {tags_text}".strip()
        return embedding_text
    
    def initialize_vector_store(self, force_recreate: bool = False):
        """
        Initialize ChromaDB vector store with questions.
        Only encodes embeddings if collection is empty or force_recreate is True.
        
        Args:
            force_recreate: If True, recreate the collection even if it exists
        """
        if self._initialized and not force_recreate:
            return
        
        # Initialize ChromaDB client FIRST (before loading model)
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        collection_name = "mcq_questions"
        
        if force_recreate:
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
        
        # Check if collection exists and has data BEFORE loading model
        collection_exists = False
        collection_has_data = False
        
        try:
            self.collection = self.client.get_collection(collection_name)
            collection_exists = True
            count = self.collection.count()
            collection_has_data = count > 0
        except:
            # Collection doesn't exist, will create it below
            collection_exists = False
            collection_has_data = False
        
        # If collection exists and has data, we're done - no encoding needed!
        if collection_exists and collection_has_data and not force_recreate:
            self._initialized = True
            return
        
        # Only now do we need to load the model and encode
        # This only happens if collection is empty or being recreated
        self._load_embedding_model()
        
        # Create collection if it doesn't exist
        if not collection_exists:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "MCQ Questions for RAG"}
            )
        
        # Load questions from JSON
        print(f"Loading questions from {self.questions_path}...")
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"Found {len(questions)} questions. Creating embeddings...")
        
        # Prepare all texts for batch encoding
        embedding_texts = []
        documents = []
        ids = []
        metadatas = []
        
        for question in questions:
            question_id = question.get("question_id", "")
            if not question_id:
                continue
            
            # Create embedding text
            embedding_text = self._create_embedding_text(question)
            embedding_texts.append(embedding_text)
            
            # Prepare metadata
            domain = self._determine_domain(question_id)
            metadata = {
                "question_id": question_id,
                "difficulty": question.get("difficulty", "unknown"),
                "tags": json.dumps(question.get("tags", [])),  # ChromaDB needs string
                "domain": domain,
                "correct_option": str(question.get("correct_option", "")),
                "option1": question.get("option1", ""),
                "option2": question.get("option2", ""),
                "option3": question.get("option3", ""),
                "option4": question.get("option4", ""),
                "question": question.get("question", "")
            }
            
            documents.append(embedding_text)
            ids.append(question_id)
            metadatas.append(metadata)
        
        # Batch encode ALL embeddings at once (much faster, no progress bars)
        print("Encoding all questions in batch...")
        embeddings = self.embedding_model.encode(
            embedding_texts, 
            show_progress_bar=False,
            batch_size=32,
            convert_to_numpy=True
        ).tolist()
        
        # Batch add to ChromaDB (in chunks to avoid memory issues)
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            self.collection.add(
                documents=batch_docs,
                embeddings=batch_embeddings,
                ids=batch_ids,
                metadatas=batch_metadatas
            )
            print(f"Added batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        
        print(f"Vector store initialized with {len(documents)} questions")
        self._initialized = True
    
    def retrieve_similar_questions(
        self, 
        query_text: str, 
        difficulty: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar questions using semantic search
        
        Args:
            query_text: Search query text
            difficulty: Filter by difficulty (easy/medium/hard)
            domain: Filter by domain
            top_k: Number of results to return
            
        Returns:
            List of question dictionaries with metadata
        """
        if not self._initialized:
            raise RuntimeError("Vector store not initialized. Call initialize_vector_store() first.")
        
        # Load model lazily only when needed for query encoding
        self._load_embedding_model()
        
        # Generate query embedding (single query, no progress bar needed)
        query_embedding = self.embedding_model.encode(
            query_text, 
            show_progress_bar=False
        ).tolist()
        
        # Build where clause for filtering
        # ChromaDB requires $and operator when multiple conditions are present
        conditions = []
        if difficulty:
            conditions.append({"difficulty": difficulty})
        if domain:
            conditions.append({"domain": domain})
        
        # Construct where clause
        if len(conditions) == 0:
            where_clause = None
        elif len(conditions) == 1:
            where_clause = conditions[0]
        else:
            where_clause = {"$and": conditions}
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )
        
        # Format results
        questions = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                question = {
                    "question_id": results['metadatas'][0][i].get("question_id", ""),
                    "question": results['metadatas'][0][i].get("question", ""),
                    "option1": results['metadatas'][0][i].get("option1", ""),
                    "option2": results['metadatas'][0][i].get("option2", ""),
                    "option3": results['metadatas'][0][i].get("option3", ""),
                    "option4": results['metadatas'][0][i].get("option4", ""),
                    "correct_option": int(results['metadatas'][0][i].get("correct_option", 1)),
                    "difficulty": results['metadatas'][0][i].get("difficulty", "unknown"),
                    "tags": json.loads(results['metadatas'][0][i].get("tags", "[]")),
                    "domain": results['metadatas'][0][i].get("domain", "unknown"),
                    "distance": results['distances'][0][i] if 'distances' in results else None
                }
                questions.append(question)
        
        return questions
    
    def retrieve_by_skills(
        self,
        skills_list: List[str],
        difficulty: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve questions by skills/keywords
        
        Args:
            skills_list: List of skills/technologies
            difficulty: Filter by difficulty
            domain: Filter by domain
            top_k: Number of results
            
        Returns:
            List of question dictionaries
        """
        # Create query from skills
        query_text = " ".join(skills_list)
        return self.retrieve_similar_questions(query_text, difficulty, domain, top_k)
    
    def get_questions_by_domain(
        self,
        domain: str,
        difficulty: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get questions by domain
        
        Args:
            domain: Domain name
            difficulty: Filter by difficulty
            top_k: Number of results
            
        Returns:
            List of question dictionaries
        """
        # Use a generic query for the domain
        query_text = domain.replace("_", " ")
        return self.retrieve_similar_questions(query_text, difficulty, domain, top_k)


# Global instance
rag_system = RAGSystem()

