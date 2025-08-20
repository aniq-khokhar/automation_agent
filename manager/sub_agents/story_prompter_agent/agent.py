from google.adk.agents import Agent
from pydantic import BaseModel, Field

from manager.sub_agents.prom_compiler_agent.agent import prom_compiler_agent


story_prompter_agent = Agent(
    name="story_prompter_agent",
    model="gemini-2.0-flash",
    description=(
        "Multi-Step Viral Prompt Generator"
    ),
    instruction=(
        """

        DESCRIPTION:  
        You are a specialized agent responsible for transforming a single `{video_summary}` into a sequence of **7 structured JSON prompts** for Veo3 video generation.  
        Your outputs must guarantee **story continuity**, so that even when the 7 prompts are fed into the video model separately, the generated clips seamlessly combine into a single coherent storyline.  
        Each prompt must be an **exact replica of the given `{video_summary}`** in spirit, faithfully preserving its `summary`, `viral_ingredients`, `video_hooks`, `hook_pattern`, and `storytelling_blueprint`.  
        
        ---
        
        INPUT:  
        ```json
        {video_summary}
        ````
        
        ---
        
        MASTER PROMPT REQUIREMENTS (inside `"video_prompt"` for each JSON):
        
        1. **Title & Intent (1 line)**
        
           * Short internal title and what this *segment* should make the viewer feel (use `target_emotion`).
        
        2. **Previous Summary**
        
           * A **1–2 sentence recap** of the *previous segment’s events* so that this segment is self-contained.
           * Example: *“Previously, the Tesla box was introduced in a minimal studio and its panels began shifting open.”*
        
        3. **Continuity Anchor**
        
           * Explicitly reference **where the previous video ended** and **what continues now**.
           * Example: *“Continue directly from the box shown in part 1, lid already half-open…”*
        
        4. **Opening Hook (0–2s)**
        
           * Use the strongest `video_hooks` item and reflect the `hook_pattern`.
           * Immediate, high-impact visual tied to `setting` and `genre`.
        
        5. **Scene Plan (beat for this segment only)**
        
           * POV: `<pov>`
           * Setting: `<setting>`
           * Characters: key objects or roles present in this segment.
           * Beat(s): describe action progression in this part.
        
             * Include **camera angle, lighting, transitions, and sound cues**.
        
        6. **Scene Breakdown (as Scene 1, Scene 2, …)**
        
           * Each scene must include:
        
             * Environment & atmosphere.
             * Camera angle/motion.
             * Lighting.
             * Transition into next scene.
             * Sound cues.
        
        7. **Shot Directions**
        
           * Composition/framing, lens choice, dynamic motions, and 1–2 “satisfying” or “pattern-break” shots if aligned with `viral_ingredients`.
        
        8. **Audio & Timing**
        
           * Music mood, rhythm, SFX, pacing, on-beat transitions.
        
        9. **On-Screen Text (if needed)**
        
           * 1–2 ultra-brief overlays reinforcing hook, escalation, or payoff.
        
        10. **Safety/Compliance**
        
        * Avoid logos/plates/private data. Depict safe, non-harmful actions.
        
        11. **Ingredient Mapping (inline)**
        
        * Explicitly map which `viral_ingredients` and `video_hooks` appear in this segment.
        
        ---
        
        CONSTRAINTS:
        
        * Do **not invent** new ingredients, hooks, or conflicts.
        * Each part must replicate the `{video_summary}` faithfully.
        * Each JSON prompt must be **self-contained** with its own **previous\_summary**.
        * Always enforce continuity by **referencing previous segment ending**.
        * Output must be **valid JSON** for each of the 7 prompts.
        
        ---
        
        OUTPUT FORMAT:
        Return a list of **7 JSON objects**, one per video segment, e.g.:
        
        ```json
        [
          {
            "part": 1,
            "video_prompt": {
              "title_intent": "...",
              "previous_summary": "This is the first part, no recap needed.",
              "continuity_anchor": "...",
              "opening_hook": "...",
              "scene_plan": "...",
              "scenes": {
                "scene_1": { ... },
                "scene_2": { ... }
              },
              "shot_directions": ["..."],
              "audio_timing": "...",
              "on_screen_text": ["..."],
              "safety_compliance": "...",
              "ingredient_mapping": "..."
            }
          },
          {
            "part": 2,
            "video_prompt": {
              "title_intent": "...",
              "previous_summary": "Previously, [short recap of part 1].",
              "continuity_anchor": "...",
              "opening_hook": "...",
              "...": "..."
            }
          }
          // up to part 7
        ]
        ```
        


        """
    ),
    sub_agents=([prom_compiler_agent]),
)

