cd ..
# dataset name and path configured in config.py
dataset=gaia-text

# model_id and server configured in model_list.py
model_id=gpt-4.1

set=0shot

python run_agent.py \
    --model-id ${model_id} \
    --set ${set}/${dataset} \
    --dataset ${dataset} \
    --task eval \
    --thinking \
    --traj_path ./traj \
    --output_path ./output \
    --run-name ${dataset}-${model_id}


# llm evaluation and print performace
python eval.py evaluate --file=WebResearcher/output/${set}/${dataset}/${dataset}-${model_id}.jsonl

