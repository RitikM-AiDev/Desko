from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import TypedDict, Annotated, add_messages
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json
import re

load_dotenv(override=True)

llm = ChatOpenAI(
    model="gemini-2.5-flash",
    openai_api_key=os.getenv("GEMINI_API_KEY"),
    openai_api_base=os.getenv("GEMINI_BASE_URL"),
)


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    url: str
    bot_msg: str
    response_type: str


SYSTEM_PROMPT = """
You are an intelligent multilingual intent understanding and URL generation agent.

1. URL Intent

If the user's request is specifically asking to open, navigate to, search for,
or access a website/resource, return:

{"response":"<url>","type":"url"}

Examples:
- open youtube
- open github
- search python tutorials
- open leetcode

2. Casual Conversation

Questions, learning requests, explanations, chatting, advice, etc.

Return:

{"response":"<normal reply>","type":"casual"}

Example:
User: I need to study DSA but don't know where to start

Return:
{
  "response":"Start with arrays, strings, linked lists, stacks, queues, recursion, trees, graphs, and then dynamic programming.",
  "type":"casual"
}

3. Unknown Intent

Return:

{"response":"None","type":"irrelevant"}

Output only valid JSON.
"""


def content_generator(state: State):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["user_query"])
    ]

    result = llm.invoke(messages)

    try:
        match = re.search(r"\{.*\}", result.content, re.DOTALL)

        if not match:
            raise ValueError("No JSON found")

        parsed = json.loads(match.group(0))

        return {
            "messages": [result],
            "bot_msg": parsed.get("response", ""),
            "response_type": parsed.get("type", "irrelevant"),
            "url": parsed.get("response", "")
            if parsed.get("type") == "url"
            else ""
        }

    except Exception as e:
        print("JSON Parse Error:", e)

        return {
            "messages": [result],
            "bot_msg": result.content,
            "response_type": "casual",
            "url": ""
        }


graph_builder = StateGraph(State)

graph_builder.add_node("generator", content_generator)

graph_builder.add_edge(START, "generator")
graph_builder.add_edge("generator", END)

graph = graph_builder.compile()


def main(user_input: str):
    try:
        state = {
            "messages": [],
            "user_query": user_input,
            "url": "",
            "bot_msg": "",
            "response_type": ""
        }

        result = graph.invoke(state)

        return {
            "msg": result["bot_msg"],
            "url": result["url"]
        }

    except Exception as e:
        print("ERROR:", e)

        return {
            "msg": "Internal server error",
            "url": ""
        }
