"""
SEE Agent Demonstration

Shows how SEE-powered autonomous agent handles tasks that AutoGPT
struggles with:
- Web search with goal validation
- Self-correction on errors
- Evidence-based termination
- No infinite loops
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from see_autogpt.agent_loop import SEEAutonomousAgent, save_agent_result


# Mock commands for demonstration
# (In real implementation, these would be actual web APIs)


def mock_web_search(query: str, max_results: int = 5) -> dict:
    """
    Mock web search command.

    In real implementation, this would call Google API, Bing, etc.
    """
    print(f"       [Searching web for: {query}]")

    # Simulate search results
    if "python tutorial" in query.lower():
        return {
            "results": [
                {
                    "title": "Python.org Official Tutorial",
                    "url": "https://docs.python.org/3/tutorial/",
                    "snippet": "The official Python tutorial covering basics to advanced topics",
                },
                {
                    "title": "Real Python Tutorials",
                    "url": "https://realpython.com/",
                    "snippet": "Comprehensive Python tutorials and courses",
                },
            ],
            "count": 2,
        }
    elif "nonexistent impossible query 12345" in query.lower():
        return {"results": [], "count": 0}
    else:
        return {
            "results": [{"title": "Generic Result", "url": "https://example.com"}],
            "count": 1,
        }


def mock_extract_content(url: str) -> dict:
    """
    Mock content extraction command.

    In real implementation, this would scrape the web page.
    """
    print(f"       [Extracting content from: {url}]")

    if "docs.python.org" in url:
        return {
            "content": "Python is a high-level programming language. "
            "This tutorial introduces the reader informally to the basic concepts...",
            "word_count": 15000,
        }
    elif "invalid" in url or url == "":
        raise ValueError("Invalid URL: cannot extract content")
    else:
        return {"content": "Generic content from website", "word_count": 50}


def mock_llm_summarize(content: str, max_words: int = 100) -> dict:
    """
    Mock LLM summarization command.

    In real implementation, this would call GPT-4 API.
    """
    print(f"       [Summarizing {len(content)} characters...]")

    if len(content) < 10:
        raise ValueError("Content too short to summarize")

    # Mock summary
    return {
        "summary": "Python is a versatile programming language with extensive documentation.",
        "word_count": 10,
    }


# Command provider: Proposes next action based on task and iteration
def simple_command_provider(task_spec: dict, iteration: int) -> dict:
    """
    Simple command provider for demonstration.

    In real AutoGPT, this would use LLM to decide next action.
    For demo, we use hard-coded logic based on iteration.
    """
    goal = task_spec.get("goal", "")

    if "python tutorial" in goal.lower():
        # Task: Find and summarize Python tutorial
        if iteration == 1:
            # First: Search for tutorial
            return {
                "name": "web_search",
                "callable": mock_web_search,
                "arguments": {"query": "python tutorial", "max_results": 5},
            }
        elif iteration == 2:
            # Second: Extract content from top result
            return {
                "name": "extract_content",
                "callable": mock_extract_content,
                "arguments": {"url": "https://docs.python.org/3/tutorial/"},
            }
        elif iteration == 3:
            # Third: Summarize content
            return {
                "name": "llm_summarize",
                "callable": mock_llm_summarize,
                "arguments": {"content": "Python is a high-level...", "max_words": 100},
            }

    # Default: search
    return {
        "name": "web_search",
        "callable": mock_web_search,
        "arguments": {"query": goal, "max_results": 5},
    }


def demo_successful_task():
    """
    Demonstrate SEE agent successfully completing a task.
    """
    print("=" * 70)
    print("DEMO 1: SEE Agent Successfully Completing Task")
    print("=" * 70)
    print()

    # Create evidence directory
    evidence_root = "/tmp/see_agent_demo"
    os.makedirs(evidence_root, exist_ok=True)

    # Initialize agent
    agent = SEEAutonomousAgent(evidence_root)

    # Define task with explicit success criteria
    task_spec = {
        "task_id": "demo_python_tutorial",
        "goal": "Find and summarize a Python tutorial",
        "success_criteria": {
            "tutorial_found": True,
            "content_extracted": True,
            "summary_generated": True,
        },
    }

    # Run task
    result = agent.run_task(
        task_spec,
        simple_command_provider,
        max_iterations=5,
        cost_budget_usd=10.00,
    )

    # Save result
    output_path = os.path.join(evidence_root, "demo_success_result.json")
    save_agent_result(result, output_path)

    print()
    print("=" * 70)
    print("RESULT:")
    print(f"  Status: {result['status']}")
    print(f"  Evidence Level: {result['final_evidence_level']}")
    print(f"  Iterations: {result['iterations']}")
    print(f"  Cost: ${result['total_cost_usd']:.2f}")
    print(f"  Criteria Met: {result['goal_criteria_met']}")
    print("=" * 70)
    print()

    return result


def demo_autogpt_style_failure():
    """
    Demonstrate how AutoGPT-style approach would fail:
    - No goal validation
    - Trusts self-reported success
    - No evidence capture
    """
    print("=" * 70)
    print("COMPARISON: How AutoGPT Would Handle This")
    print("=" * 70)
    print()

    print("AutoGPT Approach:")
    print("  1. Execute: web_search('python tutorial')")
    print("     → Returns: {'results': [...], 'count': 2}")
    print("     → Status: 'success' (command didn't crash)")
    print("     ❌ NO VALIDATION: Did we achieve the goal? Unknown.")
    print()

    print("  2. Execute: extract_content('https://...')")
    print("     → Returns: {'content': '...', 'word_count': 15000}")
    print("     → Status: 'success'")
    print("     ❌ NO VALIDATION: Is this the right content? Unknown.")
    print()

    print("  3. Cycles remaining: 0")
    print("     → Terminate: 'Out of cycles'")
    print("     ❌ GOAL NOT ACHIEVED: Never generated summary!")
    print()

    print("AutoGPT Problems:")
    print("  - No goal validation (just checks command success)")
    print("  - Terminates based on arbitrary cycle count")
    print("  - No evidence that goal was achieved")
    print("  - Cannot debug what went wrong (no receipts)")
    print()

    print("SEE Agent Advantages:")
    print("  ✅ Validates GOAL achievement, not just command success")
    print("  ✅ Evidence-based termination (E3/E4 required)")
    print("  ✅ Full audit trail with SHA256 receipts")
    print("  ✅ Self-correcting (patch provider)")
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    # Run demonstrations
    demo_autogpt_style_failure()
    result = demo_successful_task()

    print()
    print("📊 EVIDENCE TRAIL:")
    print("   Check these receipts for complete audit trail:")
    for i, receipt_path in enumerate(result["evidence_trail"], 1):
        print(f"   {i}. {receipt_path}")
    print()
