cd ..
# dataset name and path configured in config.py
dataset=anchor-urls

# model_id and server configured in model_list.py
model_id=gpt-4.1

set=0shot

python run_agent.py \
    --model-id ${model_id} \
    --set ${set}/${dataset} \
    --dataset ${dataset} \
    --task qa_construct \
    --thinking \
    --traj_path ./traj \
    --output_path ./output \
    --run-name ${dataset}-${model_id}

# result writed in output/${set}/${dataset}/${run-name}.jsonl
# formulating the constructed QA pairs
# python convert.py main --format_type=formatQuery input_path=output/${set}/${dataset}/${run-name}.jsonl output_file=/path