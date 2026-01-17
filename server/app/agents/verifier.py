"""
Verifier Agent - Validation, confidence checking, and recovery logic.

This agent:
1. Validates action correctness against mission requirements
2. Detects ambiguity or low confidence
3. Triggers retry loops when needed
4. Provides helpful feedback to players
"""

import logging
from typing import Optional

from app.models import ParsedAction, MissionState, WorldState
from app.config import config

logger = logging.getLogger(__name__)


class VerificationResult:
    """Result of action verification."""
    
    def __init__(
        self,
        is_valid: bool,
        should_execute: bool,
        should_retry: bool,
        feedback: list[str],
        grammar_score: float = 0.0,
        mission_progress: float = 0.0,
    ):
        self.is_valid = is_valid
        self.should_execute = should_execute
        self.should_retry = should_retry
        self.feedback = feedback
        self.grammar_score = grammar_score
        self.mission_progress = mission_progress
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "should_execute": self.should_execute,
            "should_retry": self.should_retry,
            "feedback": self.feedback,
            "grammar_score": self.grammar_score,
            "mission_progress": self.mission_progress,
        }


class VerifierAgent:
    """
    Validates actions against mission requirements and grammar rules.
    Provides feedback for learning purposes.
    """
    
    def __init__(self):
        self.grammar_rules = {
            "politeness": {
                "markers": ["please", "would_like", "could_i", "may_i", "thank_you", "excuse_me"],
                "weight": 0.3,
            },
            "conditional": {
                "markers": ["conditional_if", "would", "could", "might", "if_then"],
                "weight": 0.25,
            },
            "causal": {
                "markers": ["because_reason", "since", "therefore", "so_that"],
                "weight": 0.25,
            },
            "quantity": {
                "weight": 0.2,
            },
        }
    
    def verify_action(
        self,
        action: ParsedAction,
        mission: Optional[MissionState],
        world_state: WorldState,
        retry_count: int = 0,
    ) -> VerificationResult:
        """
        Verify an action meets requirements.
        Returns verification result with feedback.
        """
        feedback = []
        is_valid = True
        should_execute = True
        should_retry = False
        grammar_score = 0.0
        mission_progress = 0.0
        
        # Check confidence threshold
        if action.confidence < config.CONFIDENCE_THRESHOLD:
            if retry_count < config.MAX_RETRY_COUNT:
                feedback.append("I didn't quite catch that. Could you please repeat?")
                should_retry = True
                should_execute = False
                is_valid = False
            else:
                feedback.append("Let me try my best to understand what you meant...")
        
        # Check for unknown intent
        if action.intent.value == "unknown":
            feedback.append("I'm not sure what you want to do. Try saying 'I want to buy...' or 'Hello!'")
            is_valid = False
            if retry_count < config.MAX_RETRY_COUNT:
                should_retry = True
                should_execute = False
        
        # Check grammar based on mission requirements
        if mission:
            grammar_feedback, grammar_score = self._check_grammar_requirements(action, mission)
            feedback.extend(grammar_feedback)
            
            # Check if mission would be completed
            mission_progress = self._calculate_mission_progress(action, mission, grammar_score)
            
            if mission_progress >= 0.8:
                feedback.append("Excellent work! You've mastered this challenge.")
            elif mission_progress >= 0.5:
                feedback.append("Good attempt! You're on the right track.")
        
        # Politeness feedback
        politeness_feedback = self._check_politeness(action)
        if politeness_feedback:
            feedback.extend(politeness_feedback)
        
        return VerificationResult(
            is_valid=is_valid,
            should_execute=should_execute,
            should_retry=should_retry,
            feedback=feedback,
            grammar_score=grammar_score,
            mission_progress=mission_progress,
        )
    
    def _check_grammar_requirements(
        self,
        action: ParsedAction,
        mission: MissionState,
    ) -> tuple[list[str], float]:
        """Check if action meets mission grammar requirements."""
        feedback = []
        score = 0.5  # Base score
        
        requirement = mission.grammar_requirement.lower()
        constructs = action.grammar_features.required_constructs_present
        
        # Check for politeness requirement
        if "polite" in requirement or "please" in requirement:
            polite_markers = set(constructs) & {"please", "would_like", "could_i", "may_i", "thank_you"}
            if polite_markers:
                score += 0.3
            else:
                feedback.append("💡 Tip: Try adding 'please' or 'I would like' to be more polite.")
        
        # Check for conditional requirement
        if "conditional" in requirement or "if" in requirement:
            conditional_markers = set(constructs) & {"conditional_if", "would", "could", "might"}
            if conditional_markers:
                score += 0.3
            else:
                feedback.append("💡 Tip: Try using 'If...then' or 'I would... if' for conditional sentences.")
        
        # Check for causal requirement
        if "because" in requirement or "causal" in requirement:
            causal_markers = set(constructs) & {"because_reason", "since", "therefore"}
            if causal_markers:
                score += 0.3
            else:
                feedback.append("💡 Tip: Explain why using 'because' or 'since'.")
        
        # Check for quantity requirement
        if "quantity" in requirement:
            if action.entities.quantity is not None:
                score += 0.2
            else:
                feedback.append("💡 Tip: Don't forget to mention how many you want!")
        
        return feedback, min(score, 1.0)
    
    def _check_politeness(self, action: ParsedAction) -> list[str]:
        """Check politeness and provide feedback."""
        feedback = []
        
        if action.grammar_features.politeness.value == "rude":
            feedback.append("The merchant looks offended. Try being more polite!")
            if "be_more_polite" not in action.feedback_keys:
                feedback.append("💡 Add 'please' or start with 'Excuse me...'")
        
        return feedback
    
    def _calculate_mission_progress(
        self,
        action: ParsedAction,
        mission: MissionState,
        grammar_score: float,
    ) -> float:
        """Calculate how much progress this action makes toward mission completion."""
        progress = grammar_score * 0.5  # Grammar is 50% of progress
        
        # Intent matching
        mission_lower = mission.success_condition.lower()
        if action.intent.value != "unknown":
            if "buy" in mission_lower and action.intent.value == "buy_item":
                progress += 0.25
            elif "negotiate" in mission_lower and action.intent.value == "negotiate":
                progress += 0.25
            elif "greet" in mission_lower and action.intent.value == "greet":
                progress += 0.25
            elif "ask" in mission_lower and action.intent.value == "ask_info":
                progress += 0.25
        
        # Confidence bonus
        if action.confidence >= 0.9:
            progress += 0.15
        elif action.confidence >= 0.8:
            progress += 0.1
        
        return min(progress, 1.0)


# Global verifier instance
verifier_agent = VerifierAgent()
