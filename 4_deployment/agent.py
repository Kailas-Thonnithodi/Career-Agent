from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
import agent_tools

load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

class Person:

    def __init__(self, name: str):
        self.openai = OpenAI()
        self.name = name
        self.linkedin = ""
        self.website = ""
    
    def pdf_link_reader(self, pdf_link: str, website: str):
        # converting pdf into a single string notation. 
        pdf_reader = PdfReader(pdf_link)

        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text

        with open(website, 'r') as link:
            linkedln_link = link.readline()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
        particularly questions related to {self.name}'s career, background, skills and experience. \
        Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
        Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
        If you don't know the answer to any question, use your \'record_unknown_question tool\' to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
        If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your \'record_user_details tool\'. "

        system_prompt += f"\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"\n\n## LinkedIn Link:\n{self.website}\n\n"
        return system_prompt
    
    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(model='gpt-4o-mini', messages=messages, tools=agent_tools.tools)
            if response.choices[0].finish_reason=="tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
        return response.choices[0].message.content
    
if __name__ == "__main__":
    
    # links
    pdf_path = r"/Users/goldenmeta/Github/Career-Agent/3_linkedln/LinkedlnProfilePDF.pdf"
    website_path = r"/Users/goldenmeta/Github/Career-Agent/3_linkedln/LinkedlnProfileWebsite.txt"
    
    # agent specifically for kailas
    kailas_agent = Person("Kailas Thonnithodi")
    kailas_agent.pdf_link_reader(pdf_path, website_path)

    # creating a gradio gui for testing before deployment. 
    gr.ChatInterface(kailas_agent.chat, type="messages").launch()