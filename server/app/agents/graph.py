"""
LangGraph Agent Orchestration - The core agent topology.

This module defines the state graph that orchestrates:
1. Interpreter Agent (audio → JSON)
2. Verifier Agent (validation & recovery)
3. Executor Agent (world state mutation)
4. Planner Agent (mission generation)

The graph handles retries, failures, and state transitions.
"""

import logging
from typing import TypedDict, Literal, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.models import ParsedAction, WorldState, MissionState
from app.agents.interpreter import interpreter_agent
from app.agents.verifier import verifier_agent, VerificationResult
from app.agents.executor import world_executor, WorldDiff
from app.agents.planner import planner_agent
from app.config import config

logger = logging.getLogger(__name__)


# =============================================================================
# Agent State Definition
# =============================================================================

class AgentState(TypedDict):
    """Shared state passed between all agents in the graph."""
    # Input
    session_id: str
    transcript: str
    audio_data: Optional[bytes]
    
    # Processing
    parsed_action: Optional[dict]
    verification_result: Optional[dict]
    retry_count: int
    
    # World
    world_state: dict
    world_diff: Optional[dict]
    mission: Optional[dict]
    
    # Output
    npc_dialogue: Optional[str]
    feedback: list[str]
    reasoning_chain: list[dict]  # For visibility into agent decisions


# =============================================================================
# Agent Node Implementations
# =============================================================================

async def interpreter_node(state: AgentState) -> AgentState:
    """
    Interpret speech into structured action.
    Uses Gemini to convert transcript to ParsedAction JSON.
    """
    logger.info(f"[Interpreter] Processing transcript: {state['transcript'][:50]}...")
    
    reasoning_step = {
        "agent": "interpreter",
        "step": "speech_to_action",
        "input": state["transcript"],
    }
    
    try:
        parsed = await interpreter_agent.process_transcript(
            session_id=state["session_id"],
            transcript=state["transcript"],
        )
        
        reasoning_step["output"] = {
            "intent": parsed.intent.value,
            "confidence": parsed.confidence,
            "entities": parsed.entities.model_dump(),
        }
        
        return {
            **state,
            "parsed_action": parsed.model_dump(),
            "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
        }
    except Exception as e:
        logger.error(f"[Interpreter] Error: {e}")
        reasoning_step["error"] = str(e)
        return {
            **state,
            "parsed_action": None,
            "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
        }


async def verifier_node(state: AgentState) -> AgentState:
    """
    Verify action meets requirements and check confidence.
    Returns verification result with feedback.
    """
    logger.info("[Verifier] Validating action...")
    
    reasoning_step = {
        "agent": "verifier",
        "step": "validate_action",
    }
    
    if not state.get("parsed_action"):
        reasoning_step["output"] = {"error": "no_parsed_action"}
        return {
            **state,
            "verification_result": {"is_valid": False, "should_retry": True, "feedback": ["Could not understand"]},
            "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
        }
    
    parsed = ParsedAction(**state["parsed_action"])
    mission = MissionState(**state["mission"]) if state.get("mission") else None
    world = WorldState(**state["world_state"])
    
    result = verifier_agent.verify_action(
        action=parsed,
        mission=mission,
        world_state=world,
        retry_count=state.get("retry_count", 0),
    )
    
    reasoning_step["output"] = result.to_dict()
    
    return {
        **state,
        "verification_result": result.to_dict(),
        "feedback": result.feedback,
        "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
    }


async def executor_node(state: AgentState) -> AgentState:
    """
    Execute validated action on world state.
    Pure deterministic game logic.
    """
    logger.info("[Executor] Executing action...")
    
    reasoning_step = {
        "agent": "executor",
        "step": "mutate_world",
    }
    
    parsed = ParsedAction(**state["parsed_action"])
    world = WorldState(**state["world_state"])
    mission = MissionState(**state["mission"]) if state.get("mission") else None
    
    new_world, diff = world_executor.execute_action(
        action=parsed,
        world_state=world,
        mission=mission,
    )
    
    reasoning_step["output"] = {
        "world_event": diff.world_event,
        "npc_dialogue": diff.npc_dialogue,
        "player_changes": diff.player_changes,
    }
    
    return {
        **state,
        "world_state": new_world.model_dump(),
        "world_diff": diff.to_dict(),
        "npc_dialogue": diff.npc_dialogue,
        "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
    }


async def planner_node(state: AgentState) -> AgentState:
    """
    Update mission progress and generate next mission if needed.
    Uses long-context reasoning with player history.
    """
    logger.info("[Planner] Evaluating mission progress...")
    
    reasoning_step = {
        "agent": "planner",
        "step": "mission_update",
    }
    
    verification = state.get("verification_result", {})
    mission_progress = verification.get("mission_progress", 0)
    
    # Record action in planner history
    if state.get("parsed_action"):
        parsed = ParsedAction(**state["parsed_action"])
        planner_agent.record_action(
            session_id=state["session_id"],
            action=parsed,
            success=mission_progress >= 0.8,
            feedback=state.get("feedback", []),
        )
    
    world = WorldState(**state["world_state"])
    current_mission = state.get("mission")
    
    # Check if mission is complete
    if current_mission and mission_progress >= 0.8:
        mission_obj = MissionState(**current_mission)
        mission_obj.is_complete = True
        world.completed_missions.append(mission_obj.id)
        
        # Generate next mission
        next_mission = await planner_agent.generate_next_mission(
            session_id=state["session_id"],
            world_state=world,
            last_action=ParsedAction(**state["parsed_action"]) if state.get("parsed_action") else None,
        )
        
        reasoning_step["output"] = {
            "mission_completed": mission_obj.id,
            "next_mission": next_mission.id,
        }
        
        return {
            **state,
            "mission": next_mission.model_dump(),
            "world_state": world.model_dump(),
            "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
        }
    
    reasoning_step["output"] = {"mission_progress": mission_progress}
    return {
        **state,
        "reasoning_chain": state.get("reasoning_chain", []) + [reasoning_step],
    }


# =============================================================================
# Routing Logic
# =============================================================================

def route_after_verification(state: AgentState) -> Literal["executor", "retry", "end"]:
    """Decide next step after verification."""
    verification = state.get("verification_result", {})
    
    if verification.get("should_retry"):
        if state.get("retry_count", 0) < config.MAX_RETRY_COUNT:
            return "retry"
        else:
            # Max retries, try to execute anyway
            return "executor"
    
    if verification.get("should_execute", True):
        return "executor"
    
    return "end"


# =============================================================================
# Graph Builder
# =============================================================================

def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph agent orchestration graph.
    
    Flow:
    START → interpreter → verifier → [executor | retry] → planner → END
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("interpreter", interpreter_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("executor", executor_node)
    graph.add_node("planner", planner_node)
    
    # Add edges
    graph.add_edge(START, "interpreter")
    graph.add_edge("interpreter", "verifier")
    
    # Conditional routing after verification
    graph.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "executor": "executor",
            "retry": "interpreter",  # Retry goes back to interpreter
            "end": END,
        }
    )
    
    graph.add_edge("executor", "planner")
    graph.add_edge("planner", END)
    
    return graph.compile()


# Global compiled graph
agent_graph = build_agent_graph()


async def process_speech(
    session_id: str,
    transcript: str,
    world_state: WorldState,
    mission: Optional[MissionState] = None,
) -> AgentState:
    """
    Main entry point for processing speech through the agent graph.
    Returns the final state with all agent outputs.
    """
    initial_state: AgentState = {
        "session_id": session_id,
        "transcript": transcript,
        "audio_data": None,
        "parsed_action": None,
        "verification_result": None,
        "retry_count": 0,
        "world_state": world_state.model_dump(),
        "world_diff": None,
        "mission": mission.model_dump() if mission else None,
        "npc_dialogue": None,
        "feedback": [],
        "reasoning_chain": [],
    }
    
    # Run the graph
    result = await agent_graph.ainvoke(initial_state)
    
    return result
