import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEntry:
    session_id: str
    question: str
    response: str
    rating: int  # 1-5 scale
    feedback_text: Optional[str]
    timestamp: float
    metadata: Dict[str, Any]
    source_count: int
    confidence_score: float
    generation_time: float

    def to_dict(self):
        return asdict(self)

class FeedbackService:
    def __init__(self, feedback_file: str = "user_feedback.jsonl"):
        self.feedback_file = Path(feedback_file)
        self.feedback_file.parent.mkdir(exist_ok=True)

    def collect_feedback(
        self,
        session_id: str,
        question: str,
        response: str,
        rating: int,
        feedback_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Collect user feedback for a chat interaction"""
        try:
            if not 1 <= rating <= 5:
                raise ValueError("Rating must be between 1 and 5")

            feedback = FeedbackEntry(
                session_id=session_id,
                question=question,
                response=response,
                rating=rating,
                feedback_text=feedback_text,
                timestamp=time.time(),
                metadata=metadata or {},
                source_count=metadata.get("source_count", 0) if metadata else 0,
                confidence_score=metadata.get("confidence_score", 0) if metadata else 0,
                generation_time=metadata.get("generation_time", 0) if metadata else 0
            )

            # Append to JSONL file
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback.to_dict()) + '\n')

            logger.info(f"Feedback collected: Session {session_id}, Rating {rating}")
            return True

        except Exception as e:
            logger.error(f"Error collecting feedback: {str(e)}")
            return False

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get aggregated feedback statistics"""
        try:
            if not self.feedback_file.exists():
                return {
                    "total_feedback": 0,
                    "average_rating": 0,
                    "rating_distribution": {},
                    "recent_feedback_count": 0
                }

            ratings = []
            rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            recent_count = 0
            recent_threshold = time.time() - 7 * 24 * 3600  # Last 7 days

            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback = json.loads(line.strip())
                        rating = feedback.get('rating', 0)
                        if 1 <= rating <= 5:
                            ratings.append(rating)
                            rating_counts[rating] += 1

                        if feedback.get('timestamp', 0) > recent_threshold:
                            recent_count += 1
                    except json.JSONDecodeError:
                        continue

            avg_rating = sum(ratings) / len(ratings) if ratings else 0

            return {
                "total_feedback": len(ratings),
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_counts,
                "recent_feedback_count": recent_count,
                "satisfaction_rate": round((sum(1 for r in ratings if r >= 4) / len(ratings) * 100) if ratings else 0, 1)
            }

        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            return {"error": str(e)}

    def get_low_rated_interactions(self, rating_threshold: int = 2) -> List[Dict[str, Any]]:
        """Get interactions with low ratings for improvement analysis"""
        try:
            low_rated = []

            if not self.feedback_file.exists():
                return low_rated

            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback = json.loads(line.strip())
                        if feedback.get('rating', 5) <= rating_threshold:
                            low_rated.append({
                                "question": feedback.get("question", "")[:200],
                                "rating": feedback.get("rating"),
                                "feedback_text": feedback.get("feedback_text", ""),
                                "timestamp": datetime.fromtimestamp(feedback.get("timestamp", 0)).isoformat(),
                                "confidence_score": feedback.get("confidence_score", 0),
                                "source_count": feedback.get("source_count", 0)
                            })
                    except json.JSONDecodeError:
                        continue

            return sorted(low_rated, key=lambda x: x["timestamp"], reverse=True)[:20]  # Last 20

        except Exception as e:
            logger.error(f"Error getting low-rated interactions: {str(e)}")
            return []

    def export_training_data(self, min_rating: int = 4) -> List[Dict[str, Any]]:
        """Export high-quality Q&A pairs for training data"""
        try:
            training_pairs = []

            if not self.feedback_file.exists():
                return training_pairs

            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback = json.loads(line.strip())
                        if (feedback.get('rating', 0) >= min_rating and
                            feedback.get('confidence_score', 0) > 0.6):

                            training_pairs.append({
                                "question": feedback.get("question", ""),
                                "answer": feedback.get("response", ""),
                                "rating": feedback.get("rating"),
                                "confidence": feedback.get("confidence_score"),
                                "source_count": feedback.get("source_count", 0)
                            })
                    except json.JSONDecodeError:
                        continue

            return training_pairs

        except Exception as e:
            logger.error(f"Error exporting training data: {str(e)}")
            return []

# Global feedback service instance
feedback_service = FeedbackService("data/user_feedback.jsonl")