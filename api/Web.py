from typing import TypedDict
from dotenv import load_dotenv
import os
import json
import re
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper
from .Tools import browser_tool
load_dotenv(override=True)
llm_classifier = ChatOpenAI(
    model="gemini-2.5-flash-lite",
    openai_api_key=os.getenv("GEMINI_API_KEY"),
    openai_api_base=os.getenv("GEMINI_BASE_URL"),
)

llm_agent = ChatOpenAI(
    model="gemini-2.5-flash-lite",
    openai_api_key=os.getenv("GEMINI_API_KEY"),
    openai_api_base=os.getenv("GEMINI_BASE_URL"),
)

serper = GoogleSerperAPIWrapper()
@tool
def web_search_tool(query: str):
    """
    
    Search the web and return relevant information.
    """
    return serper.run(query)
tools = [
    browser_tool,
    web_search_tool,
]
llm_with_tools = llm_agent.bind_tools(tools)
class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    url: str
    bot_msg: str
    response_type: str
    
CLASSIFIER_PROMPT = """
You are an intent classifier.

Rules:

1. If user wants:
- a website
- online resource
- course
- documentation
- tutorial
- search result
- learning resource
- web application

Return:

{
  "type":"url"
}

2. Casual conversation:

{
  "type":"casual",
  "response":"..."
}

3. Unknown:

{
  "type":"irrelevant"
}

Output ONLY JSON.
"""
def content_generator(state: State):

    messages = [
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=state["user_query"]),
    ]

    result = llm_classifier.invoke(messages)

    try:

        match = re.search(r"\{.*\}", result.content, re.DOTALL)

        if not match:
            raise ValueError("JSON not found")

        data = json.loads(match.group())

    except Exception as e:

        print("Classifier Parse Error:", e)

        data = {
            "type": "casual",
            "response": result.content,
        }

    return {
        "messages": [],
        "response_type": data.get("type", "irrelevant"),
        "bot_msg": data.get("response", ""),
        "url": "",
    }
def url_agent(state: State):

    agent_prompt = f"""
User request:

{state['user_query']}

Use tools whenever necessary.

If user wants a learning resource,
documentation, website, course,
or search result, find the BEST URL.

Return the URL directly.

Example:
https://www.geeksforgeeks.org/data-structures/
"""

    result = llm_with_tools.invoke(
        [
            HumanMessage(content=agent_prompt)
        ]
    )
    return {
        "messages": [result]
    }
tool_node = ToolNode(tools)
def final_response(state: State):
    last_message = state["messages"][-1]
    content = str(last_message.content)
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, content)
    if match:
        url = match.group(0)
        return {
            "url": url,
            "bot_msg": url,
        }
    return {
        "url": "",
        "bot_msg": content,
    }
graph_builder = StateGraph(State)
graph_builder.add_node("generator", content_generator)
graph_builder.add_node("url_agent", url_agent)
graph_builder.add_node("tools", tool_node)
graph_builder.add_node("final", final_response)
graph_builder.add_edge(START, "generator")
graph_builder.add_conditional_edges(
    "generator",
    lambda state: (
        "url_agent"
        if state["response_type"] == "url"
        else END
    ),
)

graph_builder.add_conditional_edges(
    "url_agent",
    tools_condition,
)
graph_builder.add_edge("tools", "url_agent")
graph_builder.add_edge("url_agent", "final")
graph_builder.add_edge("final", END)
graph = graph_builder.compile()
def main(user_input: str):

    try:

        initial_state = {
            "messages": [],
            "user_query": user_input,
            "url": "",
            "bot_msg": "",
            "response_type": "",
        }

        result = graph.invoke(initial_state)

        return {
            "msg": result.get("bot_msg", ""),
            "url": result.get("url", ""),
        }

    except Exception as e:

        print("ERROR:", e)

        return {
            "msg": f"Internal Error: {str(e)}",
            "url": "",
        }
