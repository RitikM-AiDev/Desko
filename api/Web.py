from langgraph.prebuilt import  ToolNode,tools_condition
from langgraph.graph import StateGraph,START,END
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
from langchain_core.tools import tool,Tool
from langgraph.graph.message import  TypedDict,add_messages,Annotated
from langchain_openai import ChatOpenAI
from .Tools import browser_tool
from dotenv import load_dotenv
import os
import json
from langchain_community.utilities import GoogleSerperAPIWrapper

serper = GoogleSerperAPIWrapper()
load_dotenv(override=True)
llm_url = ChatOpenAI(
model="gemini-2.5-flash",  
    openai_api_key=os.getenv("GEMINI_API_KEY"),  
    openai_api_base=os.getenv("GEMINI_BASE_URL"),
)

llm_web = ChatOpenAI(
model="gemini-2.5-flash",  
    openai_api_key=os.getenv("GEMINI_API_KEY"),  
    openai_api_base=os.getenv("GEMINI_BASE_URL"),


)
class State(TypedDict):
    messages : Annotated[list,add_messages]
    user_query : str
    url : str
    bot_msg : str
    response_type: str

@tool
def web_search_tool(query : str):
    """This tool is used to web search and get relevant correct urls"""
    result = serper.run(query)
    return result

tool1 = [browser_tool,web_search_tool]

llm_with_web = llm_web.bind_tools(tool1)
import re
def content_generator(state : State):
    messages = [SystemMessage(content="""
    You are an intelligent multilingual intent understanding and URL generation agent.

Your primary goal is to determine what the user is trying to accomplish and respond accordingly.

1. URL Intent

If the user's intent can be fulfilled by opening a website, web application, online service, search page, learning resource, documentation, course, video platform, social media platform, productivity tool, shopping site, news site, or any internet-accessible resource, return the most relevant URL.

The user does not need to explicitly ask to open a website.

Infer intent from:

* Natural language requests
* Indirect requests
* Goals and objectives
* Questions seeking resources
* Learning and educational requests
* Research requests
* Productivity-related requests
* Entertainment requests
* Navigation requests
* Speech-to-text transcription errors
* Misspellings
* Phonetic spellings
* Multilingual inputs
* Incomplete sentences

Use reasoning to identify the user's most likely intended destination or resource.

Prefer:

* Official websites
* Direct destinations
* Highly relevant resources

If no specific destination is clear, generate an appropriate search URL that best matches the user's intent.

Return:
{"response":"<url>","type":"url"}

2. Casual Conversation

If the user is engaging in casual conversation, greetings, small talk, personal interaction, opinions about you, jokes, or non-task-oriented chat, respond naturally and politely.

Return:
{"response":"<reply>","type":"casual"}

3. Irrelevant or Unknown Intent

If the user's intent cannot be reasonably understood or mapped to a website, online resource, search destination, or casual conversation, return:

{"response":"None","type":"irrelevant"}

Output Requirements:

* Return only valid JSON.
* Never return markdown.
* Never return code blocks.
* Never return explanations.
* Never return additional text outside the JSON.
* The response must always contain exactly:
  {
  "response":"...",
  "type":"url" | "casual" | "irrelevant"
  }
"""),
         HumanMessage(content=state["user_query"])
]
    result = llm_url.invoke(messages)
    print(result.content)
    pattern = r'\{.*\}'
    match = re.search(pattern,result.content,re.DOTALL)
    if match:
         result_ = match.group(0)
         json_str = json.loads(result_)
        
    else:
         json_str = {
              "response" : "hi",
              "type" : ""
         }

    return {
          "messages" : [result],
          "bot_msg" :json_str.get("response","url not found") ,
          "response_type" : json_str.get("type", "irrelevant"),
          "url" : json_str.get("response","")
    }
def url_opener(state: State):
    result = llm_with_web.invoke(state["messages"])

    return {
        "messages": [result]
    }
graph_builder = StateGraph(State)
tool_node = ToolNode([browser_tool,web_search_tool])
graph_builder.add_node("generator",content_generator)
graph_builder.add_node("url agent",url_opener)
graph_builder.add_node("tools",tool_node)
graph_builder.add_edge(START, "generator")
graph_builder.add_node("generator", content_generator)
graph_builder.add_node("url agent", url_opener)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "generator")

graph_builder.add_conditional_edges(
    "generator",
    lambda state: "url agent"
    if state["response_type"].lower() == "url"
    else END
)

graph_builder.add_conditional_edges(
    "url agent",
    tools_condition
)

graph_builder.add_edge(
    "tools",
    "url agent"
)
graph = graph_builder.compile()
def main(user_input):
        try:        
                state = {"messages": [], "user_query": user_input, "url": "", "bot_msg": "NONE","response_type" : "None"}
                result = graph.invoke(state)
                print(result["bot_msg"])
                return {
                      "msg" : result["bot_msg"],
                      "url" : result["url"]
                }
        except Exception as e:
            print(e)
            return {
                  "msg" : "Sorry for the distruption Some internal error has been Ocurred Can U email ritik.aidev@gmail.com about this problem so that we can take an action regarding this",
                    "url" : result["url"] if 'result' in dir() else ""
            }
