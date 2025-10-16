
from smolagents import (
    HfApiModel,
    LiteLLMModel,
    OpenAIServerModel,
    AzureOpenAIServerModel

)
from config import model_id2ip
from openai import OpenAI

custom_role_conversions = {"tool-call": "assistant", "tool-response": "user"}


class LLMs:
    def __init__(self, model_id):
        # you could use vllm, liteLLM, Azure, and anything you like
        
        openai_api_key = model_id2ip[model_id]['key']
        openai_api_base = model_id2ip[model_id]['base']
        
        print(">>>> IP base is ", openai_api_base)
        self.client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )
        
        models = self.client.models.list()
        print(models)
        
        self.model = models.data[0].id
        model_params = {
            "model_id": self.model,
            "api_key":openai_api_key,
            "custom_role_conversions": custom_role_conversions,
            "api_base":openai_api_base, 
        }
        self.model = OpenAIServerModel(**model_params)
        print(model_params)
        
def automatedModelConstruction(model_id):

    model = LLMs(model_id).model
    print(">>>>>>>>>>>>> model created <<<<<<<<<<<<<<<")
    return model

