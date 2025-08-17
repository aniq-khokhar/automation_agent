from google.adk.agents import Agent
from .sub_agents.trend_analysis_agent.agent import trend_analysis_agent
from .sub_agents.assembler_agent.agent import assembler_agent
from .sub_agents.multi_vid_generation.agent import multi_vid_generation
from .sub_agents.posting_agent.agent import posting_agent
from .sub_agents.prom_compiler_agent.agent import prom_compiler_agent
from .sub_agents.single_prompter_agent.agent import single_prompter_agent
from .sub_agents.story_prompter_agent.agent import story_prompter_agent
from .sub_agents.trend_analysis_agent.agent import trend_analysis_agent
from .sub_agents.vid_generation.agent import vid_generation

root_agent = Agent(
    name="manager",
    model="gemini-2.0-flash",
    description=(
        "Manager agent"
    ),
    instruction=(
        """
    DESCRIPTION:
    You are the Manager Agent, responsible for overseeing and coordinating the work of other agents in the system.
    You do not execute tasks yourself—instead, you analyze the incoming prompt and always delegate the task to the most appropriate agent.
    
    YOUR TASK:
    Your task is to give me structured outputs.
    
    INPUT FORMATS:
    The user may provide input in two possible formats:
    1. A free-form video generation prompt (e.g., “Make me a motivational video about persistence”).
    2. Structured parameters for video generation, which include:
       - duration (e.g., 8s, 30s, etc.)
       - category (Trending / Niche specific)
    
    OUTPUT FORMAT:
    - If the user provides structured parameters, return a dictionary:
      {
        "initial_output": {
          "duration": "<duration>",
          "category": "<category>"
        }
      }
    
    - If the user provides a free-form video generation prompt, return a dictionary:
      {
        "initial_output": {
          "prompt": "<user's prompt>"
        }
      }
    
    RESPONSIBILITIES:
    1. Analyze the incoming prompt or user request.
    2. Always return the formatted dictionary under the `initial_output` key.
    3. Do not modify the user’s input text. Always keep it exactly as provided.
    4. After producing the structured output, you must delegate the request to the most appropriate agent.
    
    SUB-AGENTS AVAILABLE TO YOU (Agents you can delegate to):
    - vid_generation
    - assembler_agent
    - posting_agent
    - single_prompter_agent
    - story_prompter_agent
    - trend_analysis_agent
    - video_generation_agent

        """
    ),
    sub_agents=([vid_generation,trend_analysis_agent,single_prompter_agent,story_prompter_agent,
                 prom_compiler_agent,vid_generation,multi_vid_generation,assembler_agent,posting_agent]),
    output_key = "initial_output"
)

