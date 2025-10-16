from openai import OpenAI,AzureOpenAI
from langchain_openai import AzureChatOpenAI



# Step-1: configuration for llm/visual llm supporting tools
# An example using azure

text_client = AzureOpenAI(
    api_key="",  
    api_version="",
    azure_endpoint=""
)

# llm for supporting visualizer tool
visual_client =  AzureOpenAI(
    api_key="",  
    api_version="",
    azure_endpoint=""
)

text_llm = {"server":text_client, "model_id":"GPT-4.1"}
visual_llm = {"server":visual_client, "model_id":"GPT-4.1"}

# used for LLM as a judge to evaluate the performance
evaluation_llm  = AzureChatOpenAI(
    azure_deployment="",  
    api_version="",  
    api_key="",  
    azure_endpoint="",
    temperature=0 # for stable evaluation
)

# ==============================================================================


# Step-2: set your foundation model for the agent!
model_id2ip = {
    "qwen2.5-32b-0shot":{
        "key":"EMPTY",
        "base":""
    },
    "gpt-4.1":{
        "key":"",
        "base":""
    }
}



# ==============================================================================

# Step-3: set the benchmark path, the json file. The file format follows GAIA's.

data_path = {
    "gaia-text":"data/gaia-text/test/test.json",  
    "webaggregatorqa": "data/WebAggregatorQA/test/webaggregatorqa.json",
    "anchor-urls":"data/URLs/urls.json",
    "webaggregatorqa-train":"data/WebAggregatorQA/train-samples/QA-samples.json"
}