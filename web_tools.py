
import argparse
import base64
import json
import mimetypes
import os
import re
import time
import uuid
from io import BytesIO
from typing import Optional
import io


import requests
from requests.exceptions import RequestException
import PIL.Image
from PIL import Image
from dotenv import load_dotenv
from markdownify import markdownify
from huggingface_hub import InferenceClient


import selenium.webdriver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from helium import (
    start_chrome,
    kill_browser,
    find_all,
    S,
    click,
    scroll_down,
    scroll_up,
    go_to,
    write,
    set_driver,
    get_driver,
)


from smolagents import CodeAgent, DuckDuckGoSearchTool, Tool, tool, AzureOpenAIServerModel
from smolagents.agents import ActionStep
from smolagents.cli import load_model
from smolagents.tools import PipelineTool, Tool

from model_list import automatedModelConstruction
from openai import AzureOpenAI
from config import text_llm, visual_llm
from scripts.cookies import COOKIES_LIST
from scripts.text_inspector_tool import TextInspectorTool

def ask_llm(query:str) -> str:

    response = text_llm["server"].chat.completions.create(
        model=text_llm['model_id'], # model = "deployment_name".
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                    ],
                }
            ]
    )
    return response.choices[0].message.content 


def save_screenshot(memory_step, agent):
    time.sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
    driver = get_driver()
    current_step = memory_step.step_number
    if driver is not None:
        # Remove previous screenshots from logs for lean processing
        for previous_memory_step in agent.memory.steps:
            if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None

        png_bytes = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(png_bytes))
        print(f"Captured a browser screenshot: {image.size} pixels")
        memory_step.observations_images = [image.copy()]  # Create a copy to ensure it persists, important!

        # Update observations with current URL
        url_info = f"Current url: {driver.current_url}"
        memory_step.observations = (
            url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
        )

def highlight_clickable_elements():
    driver = helium.get_driver()
    
    set_driver(driver)
    # Find all clickable elements
    clickable_elements = find_all(S('a, button, input, textarea, select, [role="button"], [tabindex]:not([tabindex="-1"])'))
    
    # Iterate over the elements, add a border and label them
    for index, element in enumerate(clickable_elements, start=1):
        # Use JavaScript to add a red border and label
        driver.execute_script(
            f"var elem = arguments[0];"
            f"var label = document.createElement('span');"
            f"label.style.color = 'red';"
            f"label.style.fontSize = '10px';"
            f"label.style.position = 'absolute';"
            f"label.style.zIndex = '1000';"
            f"label.style.backgroundColor = 'white';"  # Add background to make the label more visible
            f"label.style.padding = '2px';"  # Add padding for better visibility
            f"label.style.borderRadius = '3px';"  # Add border radius for aesthetics
            f"label.style.right = '-25px';"  # Position the label outside the element
            f"label.style.top = '-25px';"    # Adjust the top position as needed
            f"label.innerText = '{index}';"
            f"elem.style.position = 'relative';"
            f"elem.style.border = '3px solid red';"
            f"elem.appendChild(label);",
            element.web_element
        )
        

        
@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """
    Searches for text on the current page via Ctrl + F and jumps to the nth occurrence.
    Args:
        text: The text to search for
        nth_result: Which occurrence to jump to (default: 1)
    """
    prompt = """
The user is looking for text on the following webpage. Please check if the webpage contains relevant content based on the text provided by the user. The reply format is as follows:

## 1. Paragraphs where the text is located (listed, All)
## 2. All occurrences of the text and the information related to it

## Text
{}
## Web Content
{} 
"""
    driver = helium.get_driver()
    url = driver.current_url
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes

    # Convert the HTML content to Markdown
    markdown_content = markdownify(response.text).strip()
    
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
    if nth_result > len(elements):
        raise Exception(f"Match n°{nth_result} not found (only {len(elements)} matches found)")
    result = f"# Found {len(elements)} matches for '{text}'."
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    result += f"# Focused on element {nth_result} of {len(elements)}\n\n # The basic information is:\n" + ask_llm(prompt.format(text, markdown_content) )
    return result


@tool
def go_back() -> None:
    """Goes back to previous page."""
    driver = helium.get_driver()
    
    driver.back()


@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up on the page. Use this to dismiss pop-up windows! This does not work on cookie consent banners.
    """
    driver = helium.get_driver()
    
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    
    
def initialize_driver():
    """Initialize the Selenium WebDriver."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--window-size=1000,1350")
    chrome_options.add_argument("--disable-pdf-viewer")
    chrome_options.add_argument("--window-position=0,0")
    driver = helium.start_chrome(headless=False, options=chrome_options)
    # for cookie in COOKIES_LIST:
    #     driver.add_cookie(cookie)
    return driver






def generate_selector(element):
    # Attempt to create a unique selector based on ID, class, or tag
    tag = element.tag_name
    element_id = element.get_attribute('id')
    element_class = element.get_attribute('class')
    
    if element_id:
        return f"{tag}#{element_id}"
    elif element_class:
        classes = ".".join(element_class.split())
        return f"{tag}.{classes}"
    else:
        return tag






def process_images_and_text(image_path, query, client):
    from transformers import AutoProcessor

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": query},
            ],
        },
    ]
    idefics_processor = AutoProcessor.from_pretrained("HuggingFaceM4/idefics2-8b-chatty")
    prompt_with_template = idefics_processor.apply_chat_template(messages, add_generation_prompt=True)

    # load images from local directory

    # encode images to strings which can be sent to the endpoint
    def encode_local_image(image_path):
        # load image
        image = PIL.Image.open(image_path).convert("RGB")

        # Convert the image to a base64 string
        buffer = BytesIO()
        image.save(buffer, format="JPEG")  # Use the appropriate format (e.g., JPEG, PNG)
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # add string formatting required by the endpoint
        image_string = f"data:image/jpeg;base64,{base64_image}"

        return image_string

    image_string = encode_local_image(image_path)
    prompt_with_images = prompt_with_template.replace("<image>", "![]({}) ").format(image_string)

    payload = {
        "inputs": prompt_with_images,
        "parameters": {
            "return_full_text": False,
            "max_new_tokens": 200,
        },
    }

    return json.loads(client.post(json=payload).decode())[0]


# Function to encode the image
def encode_image(image_path):
    if image_path.startswith("http"):
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        request_kwargs = {
            "headers": {"User-Agent": user_agent},
            "stream": True,
        }

        # Send a HTTP request to the URL
        response = requests.get(image_path, **request_kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")

        extension = mimetypes.guess_extension(content_type)
        if extension is None:
            extension = ".download"

        fname = str(uuid.uuid4()) + extension
        download_path = os.path.abspath(os.path.join("downloads", fname))

        with open(download_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=512):
                fh.write(chunk)

        image_path = download_path

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


headers = {"Content-Type": "application/json", "Authorization": f"Bearer sk-v3vzSqMLo0TxJf77440c430e75B04a90A6D02fCb0506B0D4"}


def resize_image(image_path):
    img = PIL.Image.open(image_path)
    width, height = img.size
    img = img.resize((int(width / 2), int(height / 2)))
    new_image_path = f"resized_{image_path}"
    img.save(new_image_path)
    return new_image_path





@tool
def visualizer(image_path: str, question: str = None) -> str:
    """A tool that can answer questions about attached images.

    Args:
        image_path: The path to the image on which to answer the question. This should be a local path to downloaded image.
        question: The question to answer.
    """

    add_note = False
    if not question:
        add_note = True
        question = "Please write a detailed caption for this image."
    if not isinstance(image_path, str):
        raise Exception("You should provide at least `image_path` string argument to this tool!")

    mime_type, _ = mimetypes.guess_type(image_path)
    base64_image = encode_image(image_path)


    response = visual_llm['server'].chat.completions.create(
        model=visual_llm['model_id'],
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
                    ],
                }
            ]
    )
    
    try:
        output = response.choices[0].message.content
    except Exception:
        raise Exception(f"Response format unexpected: {response.json()}")

    if add_note:
        output = f"You did not provide a particular question, so here is a detailed caption for the image: {output}"

    return output

@tool
def generate_a11y_tree() -> str:
    """Parse the webpage's accessibility tree and return the index, description, selector, URL, type, value, etc., for each element. "
    Returns:
        The accessibility tree of the webpage.
    """
    driver = helium.get_driver()
    
    set_driver(driver)
    custom_elements = driver.execute_script("""
        const elements = [];
        const allElements = document.querySelectorAll('*');
        
        
        const interactiveTags = ['a', 'button', 'input', 'textarea', 'select'];
        
        const interactiveKeywords = ['button', 'link', 'input'];
        const interactiveRoles = ['button', 'link', 'menuitem', 'checkbox', 'radio', 'dialog', 'tab', 'tabpanel'];

        allElements.forEach(element => {
            const tagName = element.tagName.toLowerCase();
            const role = element.getAttribute('role');
            
            
            if (interactiveTags.includes(tagName) && !elements.includes(tagName)) {
                elements.push(tagName);
            }
            
            
            if (tagName.includes('-')) {  
                if (interactiveKeywords.some(keyword => tagName.includes(keyword)) && !elements.includes(tagName)) {
                    elements.push(tagName);  
                }
            }
            
            if (role && interactiveRoles.includes(role) && !elements.includes(role)) {
                elements.push(role);  
            }
        });

        return elements;
    """)


    selectors = 'a'
    if custom_elements:
        selectors += ',' + ','.join(custom_elements)
    elements = find_all(S(selectors))
    index = 1
    have = set()
    tree_str = ""
    number = 300
    
    
    for element in elements:
        try:
            web_element = element.web_element
            tag_name = web_element.tag_name.lower()
            
            element_id = web_element.get_attribute('id')
            element_type = web_element.get_attribute('type')
            element_value = web_element.get_attribute('value')
            element_aria_label = web_element.get_attribute('aria-label')
            
            description = web_element.text.strip() or web_element.get_attribute('alt') or "No description"
            # description = web_element.text.strip() or web_element.get_attribute('alt') or "No description"
            url = web_element.get_attribute('href') if tag_name == 'a' else ""
            print_name = tag_name
            if tag_name=="a":
                print_name="link"
            print_name = print_name if element_aria_label is None else element_aria_label
            
            node_identifier = f"{print_name} '{description}'"
            # if url:
            #     node_identifier += f" url: {url}"
            if element_type:
                node_identifier += f" type: {element_type}"
            if element_value:
                node_identifier += f" value: {element_value}"
                
            if node_identifier not in have:
                have.add(node_identifier)
                
                if len(have) >= number:
                    continue
                
                tree_str += f"[{index}] {node_identifier}\n"
                index += 1
                
                
        except:
            pass
            
    return "The accessibility tree is:\n\n" + tree_str


def generate_a11y_tree_json():
    """Parse the webpage's accessibility tree and return the index, description, selector, URL, type, value, etc., for each element in JSON format."""
    
    driver = helium.get_driver()
    set_driver(driver)
    
    custom_elements = driver.execute_script("""
        const elements = [];
        const allElements = document.querySelectorAll('*');
        

        const interactiveTags = ['a', 'button', 'input', 'textarea', 'select'];

        const interactiveKeywords = ['button', 'link', 'input'];
        const interactiveRoles = ['button', 'link', 'menuitem', 'checkbox', 'radio', 'dialog', 'tab', 'tabpanel'];

        allElements.forEach(element => {
            const tagName = element.tagName.toLowerCase();
            const role = element.getAttribute('role');
            

            if (interactiveTags.includes(tagName) && !elements.includes(tagName)) {
                elements.push(tagName);
            }
            
            if (tagName.includes('-')) {  
                if (interactiveKeywords.some(keyword => tagName.includes(keyword)) && !elements.includes(tagName)) {
                    elements.push(tagName);  
                }
            }
            
            if (role && interactiveRoles.includes(role) && !elements.includes(role)) {
                elements.push(role);  
            }
        });

        return elements;
    """)


    selectors = 'a'
    if custom_elements:
        selectors += ',' + ','.join(custom_elements)
    elements = find_all(S(selectors))
    a11y_tree = []
    index = 1
    number = 300
    have = set()
    
    base_url = driver.current_url if driver.current_url else ""
    
    for element in elements:
        try:
            web_element = element.web_element
            tag_name = web_element.tag_name.lower()
            
            # Retrieve common element attributes
            element_id = web_element.get_attribute('id')
            element_type = web_element.get_attribute('type')
            element_value = web_element.get_attribute('value')
            element_aria_label = web_element.get_attribute('aria-label')
            
            description = web_element.text.strip() or web_element.get_attribute('alt') or "No description"
            
            # Generate a more specific selector
            selector = f"{tag_name}[type='{element_type}']" if element_type else tag_name
            if element_id:
                selector = f"{tag_name}#{element_id}"
            
            # Create the dictionary representing the element in JSON format
            item = {
                "index": index,
                "description": description,
                "category": tag_name,
                "selector": selector,
                "url": urljoin(base_url, web_element.get_attribute('href') if tag_name == 'a' else ""),
                "type": element_type or "",
                "value": element_value or ""
            }
            
            # fix
            print_name = tag_name
            if tag_name=="a":
                print_name="link"
            print_name = print_name if element_aria_label is None else element_aria_label
            # 构建节点标识符
            node_identifier = f"{print_name} '{description}'"
            # if url:
            #     node_identifier += f" url: {url}"
            if element_type:
                node_identifier += f" type: {element_type}"
            if element_value:
                node_identifier += f" value: {element_value}"
                
            if node_identifier not in have:
                have.add(node_identifier)
                
                if len(have) >= number:
                    continue
            
                # Append to the a11y tree list
                a11y_tree.append(item)
                index += 1
        except Exception as e:
            print(f"Error processing element: {e}")
            pass
    
    # Return the accessibility tree as a JSON string
    return a11y_tree

@tool
def perform_click(index: int) -> str:
    """
    Click the button or link in the website.
    Args:
        index: The index of the element in the accessibility tree.
    """
    driver= helium.get_driver()
    set_driver(driver)
    a11y_tree = generate_a11y_tree_json()
    
    item = next((x for x in a11y_tree if x["index"] == index), None)

        

    if item["url"]:
        go_to(item["url"])
    elif item["selector"]:
        click(S(item["selector"]))
    else:
        return "No valid method to perform click found"
    
    webcontent = markdownify(driver.page_source).strip()
    return "Click maybe successed! Please check it!" + f"The current web page is {webcontent}" + f"{generate_a11y_tree()}"

@tool
def perform_input( index:int, text:str, ) -> str:
    """
    Enter the text into the text box corresponding to the index.
    Args:
        index: The index of the text box in the accessibility tree.
        text: The content you want to input into the text box.
    """
    driver= helium.get_driver()
    
    set_driver(driver)
    a11y_tree = generate_a11y_tree_json()
    
    item = next((x for x in a11y_tree if x["index"] == index), None)


    if item["category"] in ['input', 'textarea'] and item["type"] not in ['button', 'submit', 'reset']:
        write(text, into=S(item["selector"]))
    else:
        return "Element is not suitable for text input"
    webcontent = markdownify(driver.page_source).strip()

    return "Text maybe successed! Please check it!"  f"The current web page is {webcontent}" + f"{generate_a11y_tree()}"

@tool
def scroll_down_window(num_pixels: int) -> None:
    """This will scroll one viewport down.
    Args:
        num_pixels: The number of pixels you want to scroll down."""
    scroll_down(num_pixels=num_pixels)
    
@tool    
def scroll_up_window(num_pixels: int) -> None:
    """This will scroll one viewport down.
    Args:
        num_pixels: The number of pixels you want to scroll up."""
    scroll_up(num_pixels=num_pixels)



def clean_web_page(web_text:str) -> str:
    prompt = """
Here is the plain text information of a webpage, which contains HTML tags as well as useful text content. Please clean up the webpage and extract the useful information. The return format should be:

## 1. Summary of the Main Content of the Webpage (short).
## 2. The complete content of the Webpage (without loss, DO NOT summarize).

The web page:
"""
    response = text_llm['server'].chat.completions.create(
        model=text_llm['model_id'], # model = "deployment_name".
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + web_text},
                    ],
                }
            ]
    )
    return response.choices[0].message.content


def set_cookies(url):
    driver= helium.get_driver()
    # COOKIES_LIST
    for cookie in COOKIES_LIST:
        if  cookie['domain'].strip(". ") in url:
            driver.add_cookie({
                "domain": cookie['domain'],
                "name": cookie['name'],
                "value": cookie['value']})
    driver.refresh()



class DownloadTool(Tool):
    name = "download_file"
    description = """
Download a file at a given URL (not a path in the computer). The file should be of this format: [".pdf",".txt",".xlsx", ".pptx", ".wav", ".mp3", ".m4a", ".png/.jpg", ".docx"]
After using this tool, for further inspection of this page you should return the download path to your manager via final_answer, and they will be able to inspect it.
RETURN FORMAT as {"file_path":path, "description":"description of the file"}.
DO NOT use this tool for .htm: for these types of files use visit_webpage with the file url instead."""

    inputs = {"url": {"type": "string", "description": "The relative or absolute url of the file to be downloaded."},
              "file_format": {"type": "string", "description": "Optional: The format of the file to be downloaded.", "nullable": True}}
    output_type = "string"

    def __init__(self, ):
        super().__init__()
        self.item=0
        # self.browser = browser

    def forward(self, url: str, file_format:str = None) -> str:
        if "arxiv" in url:
            url = url.replace("abs", "pdf")
        response = requests.get(url)
        # response = requests.get(pdf_url, headers=send_headers)
        bytes_io = io.BytesIO(response.content)
        content_type = response.headers.get("content-type", "")
        extension = mimetypes.guess_extension(content_type)
        # ind = random.choice()
        if file_format:
            extension = file_format
            if not file_format.startswith("."):
                extension = "."+extension
        elif url.endswith(".txt"):
            extension = ".txt"
        elif extension is None and "pdf" in url:
            extension = ".pdf"
        else:
            extension = ".pdf"
            
        if  "htm" in extension:
            raise Exception("Do not use this tool for html files: use visit_page instead.")
        
        if extension and isinstance(extension, str):
            new_path = f"./downloads/file-{self.item}{extension}"
        else:
            new_path = f"./downloads/file-{self.item}.object"
        self.item+=1
        
        if url.endswith(".pdf") or ".pdf" in url:
            with open(new_path, mode='wb') as f:
                f.write(bytes_io.getvalue())
        else:
            with open(new_path, "wb") as f:
                f.write(response.content)
        
        try:
            if not (new_path.endswith("jpg") or new_path.endswith("png")):
                model = automatedModelConstruction("gpt-4.1")

                text_limit = 100000
                ti_tool = TextInspectorTool(model, text_limit)
                description = ti_tool.forward(new_path)
            else:
                description = visualizer(new_path, "Describe this image.")
        except:
            description=""
            # raise Exception("The tool can ONLY download files that have explicit file suffixes in the URL. If the URL does not have a suffix, it may be necessary to open it in a browser for rendering before downloading.")
        return str({"file_path": new_path,"description":description})


visit_tool_downloader = DownloadTool()
@tool
def visit_webpage(url: str,) -> str:
    """Markdownify the webpage you visited to provide basic webpage information. Provide the accessibility tree for more precise web-related action. 

    Args:
        url: The URL of the webpage to visit.
        
    Returns:
        The content of the webpage converted to Markdown and the accessibility tree, or an error message if the request fails. Format as: `Webpage content:\n\n webpage \n\n The accessibility tree is:\n\n tree.`
    """
    from helium import wait_until
    def page_loaded():
        driver = get_driver()
        return driver.execute_script("return document.readyState") == "complete"

    info = ""
    try:
        driver = get_driver()
        set_driver(driver)
        go_to(url)
        set_cookies(url)
        wait_until(page_loaded)
    except Exception as e:
        return info + f"However, An unexpected error occurred: {str(e)}"
    
    markdown_content= ""
    try:
        driver = get_driver()
        set_driver(driver)
        markdown_content = markdownify(driver.page_source).strip()
        
        
        if url.endswith(".pdf") or  url.endswith(".txt") or "/pdf/" in url:
            markdown_content = visit_tool_downloader(url)
        elif "%PDF" in markdown_content:
            markdown_content = visit_tool_downloader(url)
        else:
            # Remove multiple line breaks
            # import re

            # def collapse_whitespace(text: str) -> str:
            #     return re.sub(r'\s+', ' ', text).strip()
            ## might hurt the document structure
            # markdown_content = collapse_whitespace(markdown_content)
            
            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
            markdown_content.replace("     "," ")
        # llm_cleaned_web = clean_web_page(markdown_content)

        return info + "Webpage content:\n\n" + markdown_content + "\n\n"+ generate_a11y_tree()

    except RequestException as e:
        info =  info + f"However, Error fetching the text content of webpage due to: {str(e)}"
    
    if markdown_content=="":
        file_content = ""
        try:
            
            file_content = visit_tool_downloader(url)
            return info + "Failed to parse the HTML. Turn to Download the Webpage content:\n\n" + file_content
        except RequestException as e:
            return info + f" Error fetching the text content of webpage due to: {str(e)}"


class MixedSearchTool(Tool):
    name = "web_search"
    description = """Performs a duckduckgo web search based on your query (think a Google search) then returns the top search results."""
    inputs = {"query": {"type": "string", "description": "The search query to perform."}}
    output_type = "string"

    def __init__(self, max_results=10, **kwargs):
        super().__init__()
        self.max_results = max_results
        try:
            from duckduckgo_search import DDGS
        except ImportError as e:
            raise ImportError(
                "You must install package `duckduckgo_search` to run this tool: for instance run `pip install dds."
            ) from e
        self.ddgs = DDGS(**kwargs)

    def forward(self, query: str) -> str:
        results = self.ddgs.text(query, max_results=self.max_results)
        if len(results) == 0:
            raise Exception("No results found! Try a less restrictive/shorter query.")
        prompt = """Here is a query, along with the Google search results. Please reorder the search results based on their relevance to the query.
## Query
{}
## Search results
{}"""
        if len(results) == 0:
            raise Exception("No results found! Try a less restrictive/shorter query.")
        postprocessed_results = [f"[{result['title']}]({result['href']})\n{result['body']}" for result in results]

        llm_processed_results = ask_llm(prompt.format(query, "## Search Results\n\n" + "\n\n".join(postprocessed_results)))
        
        
        return llm_processed_results
    
    

@tool
def simple_check_constructed_question(task: dict) -> str:
    """
    Check whether the constructed question meets the requirements and provide suggestions for modification if necessary. This should be used to check the quality of the question before using `final_answer`.
    Args:
        task: The constructed task, including question, answer, and reference URLs.
    Returns:
        Whether the `question` meets the requirements, the reasons if it does not, and possible directions for improvement.
    """
    import prompt
    response = text_llm['server'].chat.completions.create(
        model=text_llm['model_id'], 
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt.simple_task_checking.format(task = str(task))},                        
                    ],
                }
            ]
    )
    return response.choices[0].message.content