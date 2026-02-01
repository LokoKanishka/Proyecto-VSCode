import ray
import asyncio
import os
from typing import List, Dict, Any, Optional
from loguru import logger
import heapq
from openai import AsyncOpenAI
import json

@ray.remote
class PlannerActor:
    """
    Cognitive Brain of Lucy.
    Uses Tree of Thoughts (ToT) to plan sequences of actions via LLM.
    """
    def __init__(self):
        logger.info("🧠 PlannerActor initializing...")
        self.max_steps = 5
        self.breadth = 3  # Number of thoughts to generate per step
        
        # Initialize OpenAI Client (targets local vLLM or Ollama)
        base_url = os.getenv("LUCY_LLM_BASE_URL", "http://localhost:11434/v1")
        api_key = os.getenv("LUCY_LLM_API_KEY", "ollama")
        self.model_name = os.getenv("LUCY_LLM_MODEL", "llama3.1:8b")
        
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        logger.info(f"🧠 Planner connected to LLM at {base_url} (Model: {self.model_name})")
        
        # Load Skills
        from src.skills.business_tools import BusinessTools
        self.business_tools = BusinessTools()

    async def plan(self, goal: str) -> List[str]:
        """
        Main entry point. Given a high-level goal, return a plan (list of steps).
        """
        logger.info(f"🧠 Planning for goal: {goal}")
        
        # 1. Root State
        # State is represented as a list of action strings
        initial_state = []
        
        # Priority Queue for Best First Search: (-score, state_list)
        # We use negative score because heapq is a min-heap
        queue = [(0.0, initial_state)]
        visited = set()
        
        best_plan = None
        max_score = -1.0

        step_count = 0
        while queue and step_count < self.max_steps:
            # Pop best state
            score, current_plan = heapq.heappop(queue)
            score = -score # Convert back to positive
            
            logger.debug(f"🔍 Expanding state (Score: {score}): {current_plan}")
            
            # Check if goal reached (Self-Evaluation)
            if await self._is_goal_reached(goal, current_plan):
                logger.info("🎯 Goal Reached!")
                best_plan = current_plan
                break
            
            # Generate Thoughts (Next possible single actions)
            thoughts = await self._generate_thoughts(goal, current_plan, self.breadth)
            
            # Evaluate/Vote on Thoughts
            scored_thoughts = await self._evaluate_thoughts(goal, current_plan, thoughts)
            
            # Add to queue
            for thought, val_score in scored_thoughts:
                new_plan = current_plan + [thought]
                # Avoid cycles (naive string check)
                plan_str = str(new_plan)
                if plan_str not in visited:
                    visited.add(plan_str)
                    # Heuristic: Accumulate score or take max? 
                    # For ToT, we usually value the path. Let's average.
                    # Simplified: Value of this step * decay + parent score
                    new_score = val_score 
                    heapq.heappush(queue, (-new_score, new_plan))
            
            step_count += 1
            
            # Fallback if queue empty or timeout, keep track of best so far?
            if val_score > max_score:
                max_score = val_score
                best_plan = new_plan

        # If we exit loop without explicit success, return best effort
        logger.info(f"🧠 Plan finalized: {best_plan}")
        return best_plan if best_plan else ["Error: Could not generate plan"]

    async def evaluate_interaction(self, user_input: str) -> str:
        """
        Quick evaluation if we need to plan or just chat.
        """
        # Simple heuristic for now, can be upgraded to LLM call
        keywords = ["abrir", "open", "ejecutar", "run", "click", "type", "search", "buscar", 
                   "calcular", "calculate", "presupuesto", "quote", "payment", "pago", "status", "envio", "shipping"]
        
        if any(keyword in user_input.lower() for keyword in keywords):
            return "PLAN"
        return "CHAT"

    # --- Internal LLM Methods ---

    async def _generate_thoughts(self, goal: str, history: List[str], k: int) -> List[str]:
        """
        Propose k distinct next steps provided the history.
        """
        prompt = f"""
        Goal: {goal}
        History: {history}
        
        You are an automated agent controlling a Linux desktop (Wayland/xdotool).
        Available Actions:
        - Control: Open Application Launcher (Super Key)
        - Action: Type 'text'
        - Action: Press Enter
        - Action: Press Key (e.g. Return, BackSpace, Tab)
        - Tool: ShippingCalculator.calculate_shipping(destination, weight_kg)
        - Tool: PaymentStatus.check_payment_status(order_id)
        - Tool: PDFGenerator.generate_quote_pdf(items, customer_name)
        - Tool: VisualAutomation.click_element(label)
        - Tool: VisualAutomation.type_into_field(label, text)
        
        Propose {k} distinct, valid NEXT single actions to advance towards the goal.
        Return ONLY valid JSON list of strings.
        Example: ["Control: Open Application Launcher", "Action: Press 'terminal'"]
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            content = response.choices[0].message.content
            # Naive parsing - requires robust output in real prod
            # Assuming LLM behaves nicely or we filter for JSON
            # For this MVP, we try to extract the list.
            if "[" in content and "]" in content:
                 start = content.find("[")
                 end = content.rfind("]") + 1
                 json_str = content[start:end]
                 return json.loads(json_str)
            else:
                 logger.warning(f"LLM did not return JSON. Content: {content}")
                 return []
        except Exception as e:
            logger.error(f"Error generating thoughts: {e}")
            return []

    async def _evaluate_thoughts(self, goal: str, history: List[str], thoughts: List[str]) -> List[tuple]:
        """
        Score thoughts from 0.0 to 1.0.
        """
        if not thoughts:
            return []
            
        prompt = f"""
        Goal: {goal}
        History: {history}
        Proposed Next Steps: {thoughts}
        
        Rate each next step's helpfulness towards the goal on a scale of 0.0 to 1.0.
        Return ONLY a JSON list of floats corresponding to the steps order.
        Example: [0.9, 0.1, 0.5]
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = response.choices[0].message.content
             # Naive parsing
            if "[" in content and "]" in content:
                 start = content.find("[")
                 end = content.rfind("]") + 1
                 json_str = content[start:end]
                 scores = json.loads(json_str)
                 return list(zip(thoughts, scores))
            else:
                 return [(t, 0.5) for t in thoughts] # Default score
        except Exception as e:
            logger.error(f"Error evaluating thoughts: {e}")
            return [(t, 0.5) for t in thoughts]

    async def _is_goal_reached(self, goal: str, history: List[str]) -> bool:
        """
        Ask LLM if goal is satisfied.
        """
        if not history: return False
        
        prompt = f"""
        Goal: {goal}
        Executed Steps: {history}
        
        Has the goal been fully achieved? 
        Return ONLY 'YES' or 'NO'.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            content = response.choices[0].message.content.strip().upper()
            return "YES" in content
        except:
            return False
