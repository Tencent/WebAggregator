cd ..
# dataset name and path configured in config.py
dataset=webresearchqa-train

# model_id and server configured in model_list.py
model_id=gpt-4.1

set=traj_sampling

python run_agent.py \
    --model-id ${model_id} \
    --set ${set}/${dataset} \
    --dataset ${dataset} \
    --task eval \ # trajs sampled by making agent answer the questions
    --thinking \
    --traj_path ./traj \
    --output_path ./output \
    --run-name ${dataset}-${model_id}

# result writed in output/${set}/${dataset}/${dataset}-${model_id}.jsonl
# Convert the collected trajs into messages.
# Note
python convert.py main --format_type=formatTrajectory input_path=traj/${dataset}-${model_id}/${model_id} output_file=/path