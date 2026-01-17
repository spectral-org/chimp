"""
World Executor - Deterministic world state mutation.

This is a NON-AI component that:
1. Applies validated actions to world state
2. Handles NPC responses
3. Manages inventory and gold
4. Emits world state diffs
"""

import logging
from copy import deepcopy
from datetime import datetime
from typing import Optional

from app.models import (
    ParsedAction, WorldState, PlayerState, NPCState, 
    MissionState, IntentType
)

logger = logging.getLogger(__name__)


class WorldDiff:
    """Represents changes to the world state."""
    
    def __init__(self):
        self.player_changes: dict = {}
        self.npc_changes: dict[str, dict] = {}
        self.mission_changes: dict = {}
        self.npc_dialogue: Optional[str] = None
        self.world_event: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "player_changes": self.player_changes,
            "npc_changes": self.npc_changes,
            "mission_changes": self.mission_changes,
            "npc_dialogue": self.npc_dialogue,
            "world_event": self.world_event,
        }


class WorldExecutor:
    """
    Deterministic executor for world state changes.
    No AI/LLM calls - pure game logic.
    """
    
    def __init__(self):
        self.prices = {
            "apple": 5,
            "bread": 8,
            "cheese": 15,
            "meat": 25,
            "fish": 20,
            "potion": 50,
            "sword": 100,
            "shield": 80,
        }
        
        self.npc_responses = {
            "greet": {
                "friendly": "Welcome to my stall, traveler! How may I help you today?",
                "neutral": "Hello. What do you need?",
                "annoyed": "Yes, what is it?",
                "angry": "*glares* Make it quick.",
            },
            "buy_polite": {
                "friendly": "Of course! Here you go. Thank you for your business!",
                "neutral": "That will be {price} gold. Here you are.",
                "annoyed": "Fine, {price} gold.",
            },
            "buy_rude": {
                "friendly": "Hmm, a simple 'please' would be nice, but here you go.",
                "neutral": "How rude. That's {price} gold, take it or leave it.",
                "annoyed": "Excuse me?! Learn some manners!",
            },
            "negotiate_success": {
                "friendly": "You drive a hard bargain! Fine, {price} gold for you.",
                "neutral": "Alright, alright. {price} gold, final offer.",
            },
            "negotiate_fail": {
                "friendly": "I'm sorry, but I can't go any lower than that.",
                "neutral": "No deal. My prices are fair.",
                "annoyed": "Absolutely not! The price is the price!",
            },
            "insufficient_gold": "You don't have enough gold for that, traveler.",
            "item_not_found": "I'm sorry, I don't have that item.",
        }
    
    def execute_action(
        self,
        action: ParsedAction,
        world_state: WorldState,
        mission: Optional[MissionState] = None,
    ) -> tuple[WorldState, WorldDiff]:
        """
        Execute an action and return the new world state with diff.
        This is pure, deterministic logic.
        """
        new_state = deepcopy(world_state)
        diff = WorldDiff()
        
        # Find target NPC (default to first merchant)
        target_npc = None
        if action.entities.target:
            for npc in new_state.npcs:
                if npc.id == action.entities.target:
                    target_npc = npc
                    break
        if not target_npc and new_state.npcs:
            target_npc = new_state.npcs[0]
        
        # Execute based on intent
        if action.intent == IntentType.GREET:
            diff = self._execute_greet(action, new_state, target_npc, diff)
        
        elif action.intent == IntentType.BUY_ITEM:
            diff = self._execute_buy(action, new_state, target_npc, diff)
        
        elif action.intent == IntentType.NEGOTIATE:
            diff = self._execute_negotiate(action, new_state, target_npc, diff)
        
        elif action.intent == IntentType.ASK_INFO:
            diff = self._execute_ask(action, new_state, target_npc, diff)
        
        elif action.intent == IntentType.GIVE_ITEM:
            diff = self._execute_give(action, new_state, target_npc, diff)
        
        elif action.intent == IntentType.MOVE:
            diff = self._execute_move(action, new_state, diff)
        
        elif action.intent == IntentType.INTERACT:
            diff = self._execute_interact(action, new_state, target_npc, diff)
        
        else:
            diff.npc_dialogue = "Hmm? I'm not sure what you mean."
        
        # Update timestamp
        new_state.timestamp = datetime.now()
        
        return new_state, diff
    
    def _execute_greet(
        self, action: ParsedAction, state: WorldState, 
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle greeting action."""
        if not npc:
            diff.npc_dialogue = "There's no one nearby to greet."
            return diff
        
        # Politeness affects NPC mood
        if action.grammar_features.politeness.value == "polite":
            npc.mood = "friendly"
            npc.patience = min(1.0, npc.patience + 0.2)
        
        mood = npc.mood
        diff.npc_dialogue = self.npc_responses["greet"].get(mood, "Hello.")
        diff.npc_changes[npc.id] = {"mood": mood}
        
        # Track dialogue
        npc.dialogue_history.append(f"Player: {action.canonical_transcript}")
        npc.dialogue_history.append(f"{npc.name}: {diff.npc_dialogue}")
        
        return diff
    
    def _execute_buy(
        self, action: ParsedAction, state: WorldState,
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle buy action."""
        if not npc:
            diff.npc_dialogue = "There's no merchant here."
            return diff
        
        item = action.entities.item
        quantity = action.entities.quantity or 1
        
        if not item:
            diff.npc_dialogue = "What would you like to buy?"
            return diff
        
        item_lower = item.lower()
        if item_lower not in self.prices:
            diff.npc_dialogue = self.npc_responses["item_not_found"]
            return diff
        
        price = self.prices[item_lower] * quantity
        
        # Check if player has enough gold
        if state.player.gold < price:
            diff.npc_dialogue = self.npc_responses["insufficient_gold"]
            return diff
        
        # Execute transaction
        state.player.gold -= price
        state.player.inventory[item_lower] = state.player.inventory.get(item_lower, 0) + quantity
        
        # NPC response based on politeness
        is_polite = action.grammar_features.politeness.value == "polite"
        response_key = "buy_polite" if is_polite else "buy_rude"
        mood = npc.mood
        
        response_template = self.npc_responses[response_key].get(mood, "Here you go.")
        diff.npc_dialogue = response_template.format(price=price)
        
        # Update diff
        diff.player_changes = {
            "gold": -price,
            "inventory_add": {item_lower: quantity}
        }
        
        # Affect NPC mood based on politeness
        if not is_polite:
            if npc.mood == "friendly":
                npc.mood = "neutral"
            elif npc.mood == "neutral":
                npc.mood = "annoyed"
            npc.patience = max(0, npc.patience - 0.2)
        
        diff.npc_changes[npc.id] = {"mood": npc.mood}
        diff.world_event = f"Purchased {quantity} {item_lower} for {price} gold"
        
        return diff
    
    def _execute_negotiate(
        self, action: ParsedAction, state: WorldState,
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle negotiation action."""
        if not npc:
            diff.npc_dialogue = "There's no one to negotiate with."
            return diff
        
        # Check if conditional language was used
        has_conditional = "conditional_if" in action.grammar_features.required_constructs_present
        
        # Negotiation success depends on NPC mood, patience, and grammar
        success_chance = 0.3  # Base chance
        
        if has_conditional:
            success_chance += 0.3
        
        if action.grammar_features.politeness.value == "polite":
            success_chance += 0.2
        
        if npc.mood == "friendly":
            success_chance += 0.2
        elif npc.mood == "annoyed":
            success_chance -= 0.3
        elif npc.mood == "angry":
            success_chance -= 0.5
        
        # Deterministic outcome based on patience threshold
        success = success_chance > (1 - npc.patience)
        
        if success:
            response_key = "negotiate_success"
            # Apply 20% discount on next purchase (store in NPC state)
            diff.world_event = "Negotiation successful! 20% discount applied to next purchase."
        else:
            response_key = "negotiate_fail"
            npc.patience = max(0, npc.patience - 0.1)
            diff.world_event = "Negotiation failed."
        
        mood = npc.mood
        response = self.npc_responses[response_key].get(mood, "We'll see.")
        diff.npc_dialogue = response.format(price="discounted")
        diff.npc_changes[npc.id] = {"mood": mood, "patience": npc.patience}
        
        return diff
    
    def _execute_ask(
        self, action: ParsedAction, state: WorldState,
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle asking for information."""
        if not npc:
            diff.npc_dialogue = "There's no one to ask."
            return diff
        
        # Generic information responses
        if npc.role == "merchant":
            diff.npc_dialogue = f"I sell the finest goods in the bazaar! We have {', '.join(self.prices.keys())}. What interests you?"
        else:
            diff.npc_dialogue = "I'm just passing through, traveler."
        
        return diff
    
    def _execute_give(
        self, action: ParsedAction, state: WorldState,
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle giving an item."""
        if not npc:
            diff.npc_dialogue = "There's no one to give to."
            return diff
        
        item = action.entities.item
        if not item or item.lower() not in state.player.inventory:
            diff.npc_dialogue = "You don't have that item."
            return diff
        
        item_lower = item.lower()
        quantity = min(action.entities.quantity or 1, state.player.inventory.get(item_lower, 0))
        
        state.player.inventory[item_lower] -= quantity
        if state.player.inventory[item_lower] <= 0:
            del state.player.inventory[item_lower]
        
        # NPC becomes friendlier
        npc.mood = "friendly"
        npc.patience = min(1.0, npc.patience + 0.3)
        
        diff.npc_dialogue = f"Oh, thank you so much! How generous of you!"
        diff.player_changes = {"inventory_remove": {item_lower: quantity}}
        diff.npc_changes[npc.id] = {"mood": "friendly"}
        
        return diff
    
    def _execute_move(
        self, action: ParsedAction, state: WorldState, diff: WorldDiff
    ) -> WorldDiff:
        """Handle movement."""
        # Simple movement in 3D space
        target = action.entities.target
        if target:
            # Move toward named location/object
            diff.world_event = f"Moving toward {target}"
            state.player.position = (0, 0, 5)  # Placeholder
        else:
            diff.world_event = "Where would you like to go?"
        
        diff.player_changes = {"position": state.player.position}
        return diff
    
    def _execute_interact(
        self, action: ParsedAction, state: WorldState,
        npc: Optional[NPCState], diff: WorldDiff
    ) -> WorldDiff:
        """Handle generic interaction."""
        if npc:
            diff.npc_dialogue = f"{npc.name} looks at you expectantly."
        else:
            diff.world_event = "You look around the bustling bazaar."
        return diff


# Global executor instance  
world_executor = WorldExecutor()
