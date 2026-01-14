from typing import TypedDict, Annotated, Dict
from langgraph.graph import StateGraph, END
from app.models import ActionSchema, WorldState
from app.agents.verifier import VerifierAgent
from app.world.executor import WorldExecutor
from app.memory import MemoryStore
from app.agents.planner import PlannerAgent

class SimulationState(TypedDict):
    action: ActionSchema
    world_state: WorldState
    validation: Dict
    feedback: str
    mission_reqs: Dict

class SimulationGraph:
    def __init__(self, verifier: VerifierAgent, executor: WorldExecutor, planner: PlannerAgent, memory: MemoryStore):
        self.verifier = verifier
        self.executor = executor
        self.planner = planner
        self.memory = memory
        self.workflow = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SimulationState)

        # Nodes
        async def validate_node(state: SimulationState):
            validation = await self.verifier.verify_action(
                state["action"], state["world_state"], state["mission_reqs"]
            )
            return {"validation": validation}

        def execute_node(state: SimulationState):
            new_state = self.executor.apply_action(state["action"])
            return {"world_state": new_state, "feedback": "Action Executed"}

        def reject_node(state: SimulationState):
            return {"feedback": f"Action Rejected: {state['validation'].get('reason')}"}

        workflow.add_node("validate", validate_node)
        workflow.add_node("execute", execute_node)
        workflow.add_node("reject", reject_node)

        # Edges
        def check_valid(state: SimulationState):
            if state["validation"].get("valid", False):
                return "execute"
            return "reject"

        workflow.set_entry_point("validate")
        workflow.add_conditional_edges("validate", check_valid)
        workflow.add_edge("execute", END)
        workflow.add_edge("reject", END)

        return workflow.compile()
    
    async def process_action(self, action: ActionSchema, current_world: WorldState, mission_reqs: Dict) -> Dict:
        initial_state = {
            "action": action,
            "world_state": current_world,
            "validation": {},
            "feedback": "",
            "mission_reqs": mission_reqs
        }
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state
