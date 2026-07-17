"""
Errors for the agent invocation (plain HTTP relay) path.
These are NOT MCP errors — MCP only applies to agents calling
learner_context / knowledge_graph / content servers, which is a
completely separate path from this one. Keeping the naming distinct
is deliberate, after the earlier architecture correction.
"""


class AgentInvocationError(Exception):
    """Base class for all agent-invocation errors."""
    def __init__(self, request_id: str, agent_name: str, detail: str, message: str = None):
        self.request_id = request_id
        self.agent_name = agent_name
        self.detail = detail
        self.message = message or f"An error occurred while contacting {agent_name}."
        super().__init__(self.message)


class AgentTimeoutError(AgentInvocationError):
    def __init__(self, request_id: str, agent_name: str, detail: str):
        super().__init__(
            request_id, agent_name, detail,
            message=f"'{agent_name}' took too long to respond. Please try again.",
        )


class AgentUnavailableError(AgentInvocationError):
    def __init__(self, request_id: str, agent_name: str, detail: str):
        super().__init__(
            request_id, agent_name, detail,
            message=f"'{agent_name}' is currently unavailable. Please try again later.",
        )


class AgentNotFoundError(AgentInvocationError):
    def __init__(self, request_id: str, agent_name: str, detail: str):
        super().__init__(
            request_id, agent_name, detail,
            message=f"'{agent_name}' does not exist or is not live.",
        )


class InputValidationError(AgentInvocationError):
    def __init__(self, request_id: str, agent_name: str, detail: str):
        super().__init__(
            request_id, agent_name, detail,
            message="Your input doesn't match what this agent expects.",
        )