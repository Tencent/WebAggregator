# This instance is based on the run_gaia.py of https://github.com/huggingface/smolagents/tree/main/examples/open_deep_research
# Thanks for their great work! and please cite them as well!

import argparse
import json
import sys
import os

current_dir = os.path.abspath('.')
if current_dir not in sys.path:
    sys.path.insert(0, current_dir) 




import threading

from datetime import datetime
from pathlib import Path
from typing import List
from model_list import *
from config import *

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import login
from scripts.reformulator import prepare_response
from scripts.run_agents import (
    get_single_file_description,
    get_zip_description,
)
import nest_asyncio
nest_asyncio.apply()

from dotenv import load_dotenv
from scripts.text_inspector_tool import TextInspectorTool

from web_tools import *



from smolagents.vision_web_browser import (
    initialize_driver
)

from smolagents import (
    CodeAgent,
    Model,
    ToolCallingAgent
)
from helium import *
from prompt import *

from dotenv import load_dotenv


from smolagents import CodeAgent, tool
from smolagents.agents import ActionStep

AUTHORIZED_IMPORTS = [
    "requests",
    "zipfile",
    "os",
    "pandas",
    "numpy",
    "sympy",
    "json",
    "bs4",
    "pubchempy",
    "xml",
    "yahoo_finance",
    "Bio",
    "sklearn",
    "scipy",
    "pydub",
    "io",
    "PIL",
    "chess",
    "PyPDF2",
    "pptx",
    "torch",
    "datetime",
    "fractions",
    "csv",
    "helium",
    "math",
    "pandas",
    "openpyxl",
    "PIL"
]
load_dotenv(override=True)
append_answer_lock = threading.Lock()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--model-id", type=str, default="qwen3-32b-0shot")
    parser.add_argument("--run-name", type=str, required=True)
    parser.add_argument("--use-open-models", action="store_true")
    parser.add_argument("--set", type=str, default="url-ft")
    parser.add_argument("--dataset", type=str, default="gaia-text")
    parser.add_argument("--task", type=str, default="eval", help="eval, qa_construct")
    
    parser.add_argument("--traj_path", type=str, default="./traj")
    parser.add_argument("--output_path", type=str, default="./output")
    
    parser.add_argument("--thinking",action = 'store_true', default=False)
    
    args = parser.parse_args()
    return args

args = parse_args()
args.eval_ds_path = data_path[args.dataset]
args.file_path = os.path.dirname(data_path[args.dataset]) +"/files"
args.prompt = question_construct_format if args.task=="qa_construct" else eval_prompt


def create_agent_hierarchy(model: Model,save_name:str, agent_id:str, agent_name:str):
    text_limit = 100000
    ti_tool = TextInspectorTool(model, text_limit)

    manager_agent = CodeAgent(
        tools=[visualizer, ti_tool,]+[ DownloadTool(),MixedSearchTool(), go_back, 
               search_item_ctrl_f, visit_webpage, perform_click,perform_input
        ],
        model=model,
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        max_steps=30,
        verbosity_level=2,
        planning_interval=31,
        traj_save_path = f"{args.traj_path}/{save_name}/{agent_name}/{agent_id}"
        
    )

    manager_agent.python_executor("from helium import *", )
    return manager_agent


def append_answer(entry: dict, jsonl_file: str) -> None:
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with append_answer_lock, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    assert os.path.exists(jsonl_file), "File not found!"
    print("Answer exported to file:", jsonl_file.resolve())

def answer_single_question(args, example, model_id, answers_file, visual_inspection_tool):

    driver = initialize_driver()
    agent_id = example['task_id']
    model = automatedModelConstruction(model_id)
    print("Model Construction ok !")
    
    document_inspection_tool = TextInspectorTool(model, 100000)

    agent = create_agent_hierarchy(model, save_name=args.run_name, agent_id = agent_id,agent_name = args.model_id)

    augmented_question = args.prompt.format(question = example["question"])

    if example["file_name"]:
        example['file_name'] = os.path.join(args.file_path, example['file_name'])
        if ".zip" in example["file_name"]:
            prompt_use_files = "\n\nTo solve the task above, you will have to use these attached files:\n"
            prompt_use_files += get_zip_description(
                example["file_name"], example["question"], visual_inspection_tool, document_inspection_tool
            )
        else:
            prompt_use_files = "\n\nTo solve the task above, you will have to use this attached file:"
            prompt_use_files += get_single_file_description(
                example["file_name"], example["question"], visual_inspection_tool, document_inspection_tool
            )
        augmented_question += prompt_use_files

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Run agent 🚀
        if not args.thinking:
            final_result = agent.run(augmented_question+"/no_think")
        else:
            final_result = agent.run(augmented_question)
            
        agent_memory = agent.write_memory_to_messages(summary_mode=True)
        
        from copy import deepcopy
        
        agent.save_messages(deepcopy(agent.write_memory_to_messages(summary_mode=False)),)
        
        final_result = prepare_response(augmented_question, agent_memory, reformulation_model=automatedModelConstruction(args.model_id))

        output = str(final_result)
        for memory_step in agent.memory.steps:
            memory_step.model_input_messages = None
        intermediate_steps = [str(step) for step in agent.memory.steps]

        # Check for parsing errors which indicate the LLM failed to follow the required format
        parsing_error = True if any(["AgentParsingError" in step for step in intermediate_steps]) else False

        # check if iteration limit exceeded
        iteration_limit_exceeded = True if "Agent stopped due to iteration limit or time limit." in output else False
        raised_exception = False

    except Exception as e:
        print("Error on ", augmented_question, e)
        output = None
        intermediate_steps = []
        parsing_error = False
        iteration_limit_exceeded = False
        exception = e
        raised_exception = True
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    annotated_example = {
        "agent_name": model.model_id,
        "question": example["question"],
        "augmented_question": augmented_question,
        "prediction": output,
        "intermediate_steps": intermediate_steps,
        "parsing_error": parsing_error,
        "iteration_limit_exceeded": iteration_limit_exceeded,
        "agent_error": str(exception) if raised_exception else None,
        "start_time": start_time,
        "end_time": end_time,
        "task": example["task"],
        "task_id": example["task_id"],
        "true_answer": example["true_answer"],
    }
    append_answer(annotated_example, answers_file)
    driver.quit()



def get_examples_to_answer(answers_file, eval_ds) -> List[dict]:
    print(f"Loading answers from {answers_file}...")
    try:
        done_questions = pd.read_json(answers_file, lines=True)["task_id"].tolist()
        print(f"Found {len(done_questions)} previous results!")
    except Exception as e:
        print("Error when loading records: ", e)
        print("No usable records! ▶️ Starting new.")
        done_questions = []
    return [line for _,line in eval_ds.iterrows() if line["task_id"] not in done_questions]


def main():
    with open(args.eval_ds_path, encoding='utf-8') as f:
        data = json.load(f)

    eval_ds = pd.DataFrame(data)
    
    print(f"Starting run with arguments: {args}")
    print(len(eval_ds))

    answers_file = f"{args.output_path}/{args.set}/{args.run_name}.jsonl"
    tasks_to_run = get_examples_to_answer(answers_file, eval_ds)
    print("still need to process ",len(tasks_to_run))

    for example in tasks_to_run:
        answer_single_question(args, example, args.model_id, answers_file, visualizer)
    print("All tasks processed.")

if __name__ == "__main__":
    main()
