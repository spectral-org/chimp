from app.models import WorldState, ActionSchema
import time

class WorldExecutor:
    def __init__(self):
        # Initial State
        self.state = WorldState(
            timestamp=time.time(),
            entities={
                "player": {"id": "player", "x": 0, "y": 0, "z": 0, "inventory": {}},
                "npc_1": {"id": "npc_1", "x": 5, "y": 0, "z": 5, "name": "Merchant", "inventory": {"apple": 5}},
                "box_1": {"id": "box_1", "x": -3, "y": 0, "z": 2, "color": "red"}
            },
            mission_state={"active_mission_id": None, "progress": 0}
        )

    def apply_action(self, action: ActionSchema) -> WorldState:
        """
        Applies a validated action to the world state deterministically.
        """
        self.state.timestamp = time.time()
        
        player = self.state.entities["player"]
        
        if action.intent == "move":
            # Very simple movement logic for demo
            # "target" in entities could be an object ID or direction.
            # If target is an object, move towards it.
            target_id = action.entities.target
            if target_id and target_id in self.state.entities:
                target = self.state.entities[target_id]
                # Teleport for now / Move halfway
                player["x"] = (player["x"] + target["x"]) / 2
                player["z"] = (player["z"] + target["z"]) / 2
            else:
                # Default move forward
                player["z"] += 1

        elif action.intent == "buy_item":
            item = action.entities.item
            qty = action.entities.quantity or 1
            # Simplify: Magic buying
            player["inventory"][item] = player["inventory"].get(item, 0) + qty

        elif action.intent == "give_item":
            item = action.entities.item
            target_id = action.entities.target
            if item in player["inventory"] and player["inventory"][item] > 0:
                player["inventory"][item] -= 1
                if target_id and target_id in self.state.entities:
                     npc = self.state.entities[target_id]
                     npc["inventory"] = npc.get("inventory", {})
                     npc["inventory"][item] = npc["inventory"].get(item, 0) + 1
        
        return self.state
