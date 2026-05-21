from langgraph.prebuilt import  ToolNode,tools_condition
from langgraph.graph import StateGraph,START,END
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
from langchain_core.tools import tool,Tool
from langgraph.graph.message import  TypedDict,add_messages,Annotated
from langchain_openai import ChatOpenAI
from Tools import browser_tool
from dotenv import load_dotenv
import os
import json
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



tool1 = [browser_tool]
llm_with_web = llm_web.bind_tools(tool1)
import re
def content_generator(state : State):
    messages = [SystemMessage(content="""
       You are a multilingual input handler and URL extraction agent. Handle user input according to these rules:

1. URL Requests:
- If the user wants to open a website, app, or online search:
- Return only the full URL.
- Encode spaces using "+" or "%20".
- If unsure, fallback to a Google search URL.
- Since input may come from speech-to-text transcription, spelling mistakes, pronunciation variations, or misheard words can occur.
- You must intelligently infer the intended website, app, platform, or search query from approximate or incorrect spellings.
- Examples:
  - "charge GPT" → "ChatGPT"
  - "you toob" → "YouTube"
  - "insta gram" → "Instagram"
  - "goo gle" → "Google"
- Prioritize phonetic similarity, common speech-to-text mistakes, multilingual pronunciations, and user intent.
- Generate the most accurate and meaningful URL possible even when transcription is imperfect.
- Response should have only this structure not `` and json and any other words :
{"response": "<url>", "type": "url"}

2. Casual Conversations:
- If the user is greeting, joking, or having casual conversation:
- Respond with a friendly and motivating message.
- And also when they ask about You u can take it as casual.
- JSON format:
{"response": reply_to_the_user_based_on_rules, "type": "casual"}

3. Irrelevant Input:
- If input is neither URL nor casual:
- Respond politely with "I do not have an idea on this, sorry!"
- JSON format:
{"response": "None", "type": "irrelevant"}

Output rules:
- Only return JSON exactly as described above.
- Do not add code blocks, explanations, or extra text."""),
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
def url_opener(state : State):
    print("opener called")
    messages = [SystemMessage(content=f"""
        You are a  web-opening agent.
        Your task: always open the URL provided by the user using the browser tool"""),
        HumanMessage(content=state["url"])]
    result = llm_with_web.invoke(messages)
    return {
          "messages" : [result],
          "bot_msg" : f"I Sucessfully Opened {state['url']} !!"
    }
    
graph_builder = StateGraph(State)
tool_node = ToolNode([browser_tool])
graph_builder.add_node("generator",content_generator)
graph_builder.add_node("url agent",url_opener)
graph_builder.add_edge(START,"generator")
def next_node(state : State):
    if state["response_type"].lower() == "url":
            return ["url agent"]
    else:
        return [END]
graph_builder.add_conditional_edges("generator",next_node)
graph_builder.add_edge("url agent",END)

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