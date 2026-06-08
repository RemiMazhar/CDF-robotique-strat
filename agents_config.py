# Module paths for each player's agent.
# The module must define a class named Agent with a make_decision(self) method.
# A separate Agent() instance is created per player, so each gets its own
# `self` for memory — even when both slots name the same module.
# Example: "agents.random_agent" loads agents/random_agent.py

PLAYER0_AGENT = "agents.simple_agent"
PLAYER1_AGENT = "agents.simple_agent"
