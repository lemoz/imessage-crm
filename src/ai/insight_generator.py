"""
Insight Generator module for creating actionable insights from conversation analysis.
Generates summaries, relationship health scores, and conversation patterns.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
from collections import Counter
import statistics

logger = logging.getLogger(__name__)

class InsightGenerator:
    """Generates insights from analyzed conversations and historical data."""
    
    def __init__(self):
        """Initialize the insight generator."""
        self.logger = logger
        
    def generate_conversation_summary(self, analysis: Dict[str, Any], max_length: int = 200) -> str:
        """
        Generate a concise summary from conversation analysis.
        
        Args:
            analysis: Analysis dictionary from ConversationAnalyzer
            max_length: Maximum length of summary in characters
            
        Returns:
            Concise summary string
        """
        summary = analysis.get('summary', '')
        if len(summary) > max_length:
            summary = summary[:max_length-3] + '...'
        return summary
    
    def calculate_relationship_health(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate relationship health score based on conversation patterns.
        
        Args:
            conversation_history: List of analyzed conversations over time
            
        Returns:
            Dictionary containing:
                - health_score: 0-100 score
                - factors: Contributing factors to the score
                - trend: improving/stable/declining
                - recommendations: List of recommendations
        """
        if not conversation_history:
            return self._get_default_health_score()
        
        # Calculate various metrics
        sentiments = [conv.get('sentiment', 0) for conv in conversation_history]
        response_times = self._calculate_response_times(conversation_history)
        conversation_frequency = self._calculate_frequency(conversation_history)
        engagement_depth = self._calculate_engagement_depth(conversation_history)
        
        # Calculate component scores
        sentiment_score = (statistics.mean(sentiments) + 1) * 50  # Convert -1 to 1 range to 0-100
        response_score = self._score_response_times(response_times)
        frequency_score = self._score_frequency(conversation_frequency)
        engagement_score = self._score_engagement(engagement_depth)
        
        # Weighted average for final score
        weights = {
            'sentiment': 0.3,
            'response': 0.25,
            'frequency': 0.25,
            'engagement': 0.2
        }
        
        health_score = (
            sentiment_score * weights['sentiment'] +
            response_score * weights['response'] +
            frequency_score * weights['frequency'] +
            engagement_score * weights['engagement']
        )
        
        # Determine trend
        trend = self._calculate_trend(conversation_history)
        
        # Generate factors and recommendations
        factors = self._identify_health_factors(
            sentiment_score, response_score, frequency_score, engagement_score
        )
        recommendations = self._generate_health_recommendations(factors, health_score)
        
        return {
            'health_score': round(health_score, 1),
            'factors': factors,
            'trend': trend,
            'recommendations': recommendations,
            'metrics': {
                'sentiment_score': round(sentiment_score, 1),
                'response_score': round(response_score, 1),
                'frequency_score': round(frequency_score, 1),
                'engagement_score': round(engagement_score, 1)
            }
        }
    
    def identify_conversation_patterns(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identify patterns in conversation history.
        
        Returns:
            Dictionary containing:
                - common_topics: Most frequently discussed topics
                - peak_times: When conversations typically happen
                - conversation_types: Distribution of conversation types
                - typical_length: Average conversation length
                - initiation_pattern: Who typically starts conversations
        """
        if not conversation_history:
            return {}
        
        # Aggregate topics
        all_topics = []
        for conv in conversation_history:
            all_topics.extend(conv.get('topics', []))
        topic_counts = Counter(all_topics)
        
        # Analyze conversation types
        conv_types = [conv.get('conversation_type', 'unknown') for conv in conversation_history]
        type_distribution = Counter(conv_types)
        
        # Calculate average length
        lengths = [conv.get('message_count', 0) for conv in conversation_history]
        avg_length = statistics.mean(lengths) if lengths else 0
        
        return {
            'common_topics': topic_counts.most_common(5),
            'conversation_types': dict(type_distribution),
            'typical_length': round(avg_length, 1),
            'total_conversations': len(conversation_history)
        }
    
    def generate_follow_up_insights(self, analysis: Dict[str, Any], contact_history: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate insights for follow-up actions.
        
        Args:
            analysis: Current conversation analysis
            contact_history: Historical data about the contact
            
        Returns:
            Dictionary containing:
                - should_follow_up: Boolean
                - urgency: low/medium/high
                - suggested_timing: When to follow up
                - follow_up_topics: What to follow up about
                - suggested_approach: How to approach the follow-up
        """
        follow_up_needed = analysis.get('follow_up_needed', False)
        urgency = analysis.get('urgency_level', 'low')
        action_items = analysis.get('action_items', [])
        
        # Determine timing based on urgency and relationship
        timing_map = {
            'high': 'within 24 hours',
            'medium': 'within 2-3 days',
            'low': 'within a week'
        }
        suggested_timing = timing_map.get(urgency, 'at your convenience')
        
        # Extract follow-up topics
        follow_up_topics = []
        if action_items:
            follow_up_topics.extend([item.get('description', '') for item in action_items[:3]])
        
        # Add unresolved topics from analysis
        if analysis.get('next_steps'):
            follow_up_topics.extend(analysis['next_steps'][:2])
        
        # Determine approach based on sentiment and relationship
        sentiment = analysis.get('sentiment_label', 'neutral')
        tone = analysis.get('suggested_response_tone', 'professional')
        
        approach_suggestions = {
            'positive': f"Continue with a {tone} tone, building on the positive momentum",
            'neutral': f"Maintain a {tone} approach, focusing on clear communication",
            'negative': f"Use an empathetic and {tone} tone to address concerns"
        }
        
        suggested_approach = approach_suggestions.get(sentiment, f"Use a {tone} tone")
        
        return {
            'should_follow_up': follow_up_needed,
            'urgency': urgency,
            'suggested_timing': suggested_timing,
            'follow_up_topics': follow_up_topics[:5],  # Limit to 5 topics
            'suggested_approach': suggested_approach,
            'action_required': len(action_items) > 0
        }
    
    def _calculate_response_times(self, conversation_history: List[Dict[str, Any]]) -> List[float]:
        """Calculate average response times from conversation history."""
        # This would need actual message timestamps to calculate properly
        # For now, return placeholder data
        return [1.5, 2.0, 1.0, 3.0]  # Hours
    
    def _calculate_frequency(self, conversation_history: List[Dict[str, Any]]) -> float:
        """Calculate conversation frequency (conversations per week)."""
        if len(conversation_history) < 2:
            return 0.0
        
        # This would need actual dates to calculate properly
        # For now, return placeholder
        return len(conversation_history) / 4.0  # Assume 4 weeks
    
    def _calculate_engagement_depth(self, conversation_history: List[Dict[str, Any]]) -> float:
        """Calculate average engagement depth (messages per conversation)."""
        message_counts = [conv.get('message_count', 0) for conv in conversation_history]
        return statistics.mean(message_counts) if message_counts else 0.0
    
    def _score_response_times(self, response_times: List[float]) -> float:
        """Score response times (0-100, faster is better)."""
        if not response_times:
            return 50.0
        
        avg_hours = statistics.mean(response_times)
        # Score: 100 for <1hr, 75 for <4hr, 50 for <24hr, 25 for >24hr
        if avg_hours < 1:
            return 100.0
        elif avg_hours < 4:
            return 75.0
        elif avg_hours < 24:
            return 50.0
        else:
            return 25.0
    
    def _score_frequency(self, frequency: float) -> float:
        """Score conversation frequency (0-100)."""
        # Score: 100 for daily, 75 for few times/week, 50 for weekly, 25 for less
        if frequency >= 7:
            return 100.0
        elif frequency >= 3:
            return 75.0
        elif frequency >= 1:
            return 50.0
        else:
            return 25.0
    
    def _score_engagement(self, avg_messages: float) -> float:
        """Score engagement depth (0-100)."""
        # Score based on average messages per conversation
        if avg_messages >= 20:
            return 100.0
        elif avg_messages >= 10:
            return 75.0
        elif avg_messages >= 5:
            return 50.0
        else:
            return 25.0
    
    def _calculate_trend(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Calculate relationship trend (improving/stable/declining)."""
        if len(conversation_history) < 3:
            return 'stable'
        
        # Compare recent vs older sentiments
        recent = conversation_history[-3:]
        older = conversation_history[:-3]
        
        recent_sentiment = statistics.mean([c.get('sentiment', 0) for c in recent])
        older_sentiment = statistics.mean([c.get('sentiment', 0) for c in older])
        
        if recent_sentiment > older_sentiment + 0.2:
            return 'improving'
        elif recent_sentiment < older_sentiment - 0.2:
            return 'declining'
        else:
            return 'stable'
    
    def _identify_health_factors(self, sentiment: float, response: float, 
                                frequency: float, engagement: float) -> List[str]:
        """Identify factors contributing to relationship health."""
        factors = []
        
        if sentiment >= 75:
            factors.append("Positive conversation sentiment")
        elif sentiment < 50:
            factors.append("Low conversation sentiment")
        
        if response >= 75:
            factors.append("Quick response times")
        elif response < 50:
            factors.append("Slow response times")
        
        if frequency >= 75:
            factors.append("Frequent communication")
        elif frequency < 50:
            factors.append("Infrequent communication")
        
        if engagement >= 75:
            factors.append("Deep, meaningful conversations")
        elif engagement < 50:
            factors.append("Brief, surface-level exchanges")
        
        return factors
    
    def _generate_health_recommendations(self, factors: List[str], score: float) -> List[str]:
        """Generate recommendations based on health factors."""
        recommendations = []
        
        if score < 50:
            recommendations.append("Consider reaching out more frequently")
            recommendations.append("Focus on more meaningful conversations")
        elif score < 75:
            recommendations.append("Maintain current communication pattern")
            recommendations.append("Look for opportunities to deepen engagement")
        else:
            recommendations.append("Continue current positive communication pattern")
        
        if "Slow response times" in factors:
            recommendations.append("Try to respond to messages more promptly")
        
        if "Low conversation sentiment" in factors:
            recommendations.append("Address any underlying concerns or conflicts")
        
        return recommendations[:3]  # Limit to 3 recommendations
    
    def _get_default_health_score(self) -> Dict[str, Any]:
        """Return default health score when no data available."""
        return {
            'health_score': 50.0,
            'factors': ['Insufficient data for analysis'],
            'trend': 'unknown',
            'recommendations': ['Continue building conversation history for better insights'],
            'metrics': {
                'sentiment_score': 50.0,
                'response_score': 50.0,
                'frequency_score': 50.0,
                'engagement_score': 50.0
            }
        }