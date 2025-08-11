from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

trend_analysis_agent = Agent(
    name="trend_analysis_agent",
    model="gemini-2.0-flash",
    description=(
        "Trend agent which analyze what's trending online"
    ),
    instruction=(
        """
        
        
        """
    ),
    tools=([]),
    sub_agents=([]),
    # tools=[get_weather, get_current_time]
)

