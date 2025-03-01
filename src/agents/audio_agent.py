# audio_agent.py
import operator
from typing import Annotated, Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# Import our cost tracker
from .cost_tracker import CostTracker


# Define the structure of the final summary
class Section(BaseModel):
    name: str = Field(description="The name of the section of the final summary.")
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section."
    )


class Sections(BaseModel):
    sections: List[Section] = Field(description="The sections of the final summary.")


# Graph State
class State(TypedDict):
    transcription: str
    transcription_language: str
    sections: list[Section]
    completed_sections: Annotated[list, operator.add]
    final_summary: str
    cost_summary: dict


class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]


class AudioAgent:
    """Agent for processing audio transcriptions and creating summaries"""

    def __init__(self, model_name="gpt-4o-mini", temperature=0):
        # Create the cost tracker
        self.cost_tracker = CostTracker(model_name=model_name)

        # Create the LLM and add our cost tracker
        self.llm = ChatOpenAI(
            model=model_name, temperature=temperature, callbacks=[self.cost_tracker]
        )

        # Create LLM with structured output
        self.planner = self.llm.with_structured_output(Sections)

        # Build the orchestrator once
        self.orchestrator_worker = self._build_orchestrator()

    def orchestrator(self, state: State):
        """Orchestrator that generates a plan for the summary"""
        # Set current node for cost tracking
        self.cost_tracker.set_current_node("orchestrator")

        summary_sections = self.planner.invoke(
            [
                SystemMessage(
                    content=f"Generate a plan for the summary in {state['transcription_language']}. Do not include introduction or conclusion, rather, focus on the main topics and specific details accompanying them."
                ),
                HumanMessage(
                    content=f"Here is the trascription from the audio: {state['transcription']}"
                ),
            ]
        )
        return {"sections": summary_sections.sections}

    def summarize_audio(self, state: WorkerState):
        """Worker writes a section of the audio transcription summary"""
        # Set current node for cost tracking
        self.cost_tracker.set_current_node("summarize_audio")

        summary = self.llm.invoke(
            [
                SystemMessage(
                    content=f"Write a summary section following the provided topic name and description. Include no preamble for each section. Make sure it is in appropriate language."
                ),
                HumanMessage(
                    content=f"Here is the section name: {state['section'].name} and description: {state['section'].description}"
                ),
            ]
        )
        return {"completed_sections": [summary.content]}

    def synthesizer(self, state: State):
        """Synthesizes the final summary from the completed sections"""
        completed_sections = state["completed_sections"]
        completed_summary = "\n\n".join(completed_sections)

        completed_summary_len = len(completed_summary)
        telegram_len_limit = 4096

        instructions = f"""
            The summary is too long. Please summarize it further while keeping the tone and style without change. Keep in mind telegram's character limit is {telegram_len_limit} and the current summary is {completed_summary_len}.
            
            Place the title and the summary in the following format:
            <b>Topic1:</b> <i>Summary of the topic</i>
            <b>Topic2:</b> <i>Summary of the topic</i>

            IMPORTANT: Make sure your final summary is formmatted with ONLY <b></b> for bold and <i></i> for italics. Nothing more is allowed. 
            Bold the titles instead of using <h2> tags.
            """

        completed_summary = self.llm.invoke(
            [
                SystemMessage(content=instructions),
                HumanMessage(content=completed_summary),
            ]
        ).content

        # Get cost summary
        cost_summary = self.cost_tracker.get_cost_summary()

        return {"final_summary": completed_summary, "cost_summary": cost_summary}

    def assign_workers(self, state: State):
        """Assigns workers to write the sections of the summary"""
        return [Send("summarize_audio", {"section": s}) for s in state["sections"]]

    def _build_orchestrator(self):
        """Build the orchestrator graph"""
        orchestrator_worker_builder = StateGraph(State)

        # Add the nodes
        orchestrator_worker_builder.add_node("orchestrator", self.orchestrator)
        orchestrator_worker_builder.add_node("summarize_audio", self.summarize_audio)
        orchestrator_worker_builder.add_node("synthesizer", self.synthesizer)

        # Add edges to connect nodes
        orchestrator_worker_builder.add_edge(START, "orchestrator")
        orchestrator_worker_builder.add_conditional_edges(
            "orchestrator", self.assign_workers, ["summarize_audio"]
        )
        orchestrator_worker_builder.add_edge("summarize_audio", "synthesizer")
        orchestrator_worker_builder.add_edge("synthesizer", END)

        return orchestrator_worker_builder.compile()

    def process_transcription(self, transcription, language="es", print_cost=True):
        """Process a transcription and generate a summary

        Args:
            transcription: The text transcription to summarize
            language: The language of the transcription (default: "es")
            print_cost: Whether to print the cost summary (default: True)

        Returns:
            dict: The summary and cost information
        """
        # Reset the cost tracker for a new run
        self.cost_tracker = CostTracker(model_name=self.llm.model_name)

        # Update the LLM with the new cost tracker
        self.llm.callbacks = [self.cost_tracker]

        # Run the workflow
        state = self.orchestrator_worker.invoke(
            {"transcription": transcription, "transcription_language": language}
        )

        # Print cost summary if requested
        if print_cost:
            cost_summary = state["cost_summary"]
            print("\n===== Cost Summary =====")
            print(f"Model: {cost_summary['model']}")
            print(f"Total Cost: {cost_summary['total_cost']}")
            print(f"Total Tokens: {cost_summary['total_tokens']}")
            print(f"API Calls: {cost_summary['calls']}")
            print(f"Duration: {cost_summary['duration_seconds']} seconds")

            print("\nCost per node:")
            for node, data in cost_summary["cost_per_node"].items():
                print(
                    f"  - {node}: {data['cost']} ({data['total_tokens']} tokens, {data['calls']} calls)"
                )
            print("========================\n")

        return {
            "summary": state["final_summary"],
            "cost_summary": state["cost_summary"],
        }
