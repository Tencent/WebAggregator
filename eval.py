import os
import fire
import json
from tqdm import tqdm
import pandas as pd
from utils import *
from langchain.evaluation import load_evaluator
from config import evaluation_llm

evaluator = load_evaluator("cot_qa",llm=evaluation_llm)

def calc_performance(data_file, ref_file="", key='task'):

    data_df = pd.read_json(data_file)

    if key not in data_df.columns:
        assert ref_file != "", f"Key '{key}' missing in data and no reference file provided"
        ref_df = pd.read_json(ref_file)

        ref_mapping = pd.Series(ref_df[key].values, index=ref_df['question']).to_dict()
        data_df[key] = data_df['question'].map(ref_mapping)

    if isinstance(data_df.loc[0, 'llm_evaluation'], dict):
        data_df['score'] = data_df['llm_evaluation'].apply(lambda x: x['score'])
    else:
        data_df['score'] = data_df['llm_evaluation'].apply(
            lambda x: pd.read_json(x)['score'] if isinstance(x, str) else x['score']
        )

    avg_score = data_df['score'].mean()
    count_by_key = data_df.groupby(key)['score'].count()
    mean_by_key = data_df.groupby(key)['score'].mean()
    sum_by_key = data_df.groupby(key)['score'].sum()

    print(f"Average score is: {avg_score}")
    print(f"Number of entries grouped by '{key}':\n{count_by_key}")
    print(f"Mean scores grouped by '{key}':\n{mean_by_key}")
    print(f"Sum of scores grouped by '{key}':\n{sum_by_key}")

    return data_df


def evaluate(file):
    data = read_jsonl(file)
    output_dir = os.path.join(os.path.dirname(file), "evaluate")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    result_path = os.path.join(output_dir, os.path.basename(file))
    result = []
    if os.path.exists(result_path):
        result = read_json(result_path)
    else:
        result = []

    for sample in tqdm(data[len(result):]):
        prediction = sample.get("prediction")
        if prediction:
            try:
                response = evaluator.evaluate_strings(
                    prediction=sample["prediction"],
                    input=sample["question"],
                    reference=sample["true_answer"]
                )
                sample['llm_evaluation'] = response
            except Exception:
                sample['llm_evaluation'] = {
                    "reasoning": "",
                    "value": "INCORRECT",
                    "score": 0
                }
        else:
            sample['llm_evaluation'] = {
                "reasoning": "",
                "value": "INCORRECT",
                "score": 0
            }
        result.append(sample)

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

    calc_performance(result_path)


def main():
    fire.Fire({
        'evaluate': evaluate, # (1) perform LLM-as-judge to evaluate the model prediction, and (2) obtain the metrics
        'calc_performance': calc_performance, # (2)obtain the metrics
    })


if __name__ == '__main__':
    main()