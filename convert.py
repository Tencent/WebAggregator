from utils import *
import ast
import os
from tqdm import tqdm
import fire
def formattingQuery(data):
    """
    Process a list of data entries, extract and parse the last 'action_output' from 
    'intermediate_steps', rename keys, add metadata, and filter invalid entries.
    """

    print("overall nums:", len(data))

    agent_error_count = 0
    extracted_strings = []

    for entry in data:
        # Count entries with agent errors
        if entry.get('agent_error') is not None:
            agent_error_count += 1

        try:
            last_step = entry['intermediate_steps'][-1]
            action_output = last_step.split("action_output")[-1].strip("=')")
            extracted_strings.append(action_output)
        except Exception:
            pass

    def parse_to_dict(text):
        """Safely evaluate string to dict and reformat keys appropriately."""
        try:
            # Convert text to dictionary
            result = ast.literal_eval(text)

            if 'answer' in result:
                result['true_answer'] = result['answer']
                del result['answer']

            if 'context' not in result:
                result['context']  # avoid trigger error

            # Add extra metadata
            result['task'] = 1
            # `task_id` is a Must
            result['task_id'] = hash(result['question'])
            result['file_name'] = ""

            return result
        except Exception as e:
            return {"_error": str(e)}

    # Parse extracted strings and exclude those with errors
    formatted = [
        parsed for s in extracted_strings
        if not ("_error" in (parsed := parse_to_dict(s.replace('\"', '"'))))
    ]

    print("agent_error:", agent_error_count)
    print("successful query:", len(formatted))
    return formatted


def formattingTrajectory(path, ref_file=None, _planning=False, _thinking=False):
    """
    Read and process JSON trajectory data from files, optionally filter using a 
    reference file, prepend tokens to assistant messages, and format the conversation.
    """

    role_replacement = {
        "MessageRole.USER": "user",
        "MessageRole.ASSISTANT": "assistant",
        "MessageRole.SYSTEM": "system",
        "MessageRole.TOOL_CALL": "tool-call",
        "MessageRole.TOOL_RESPONSE": "user",
    }

    def prepend_token(data):
        """
        Prepend <think></think> token to assistant messages for Qwen3 models.
        """
        for message in data['messages']:
            if message['role'] == "assistant":
                if not message['content'].strip().startswith("<think></think>"):
                    message['content'] = "<think></think>\n" + message['content'].strip()
                assert message['content'].count("<think></think>") == 1
        return data

    # List all files ending with '-1.json' in subdirectories of path
    files = [
        os.path.join(path, file, "-1.json")
        for file in os.listdir(path)
        if os.path.exists(os.path.join(path, file, "-1.json"))
    ]

    filtered_questions = set()
    
    # step-1: Filter out no prediction, unable to determine
    if (d.get('prediction') and "unable to determine" in d['prediction'].lower()) or \
            not d.get('prediction') :
        filtered_questions.add(d['augmented_question'])
    
    if ref_file is not None:
        ref_data = read_jsonl(ref_file)
        for d in ref_data:
            # step-2: filter failed questions
            if d.get("eval") is False:
                filtered_questions.add(d['augmented_question'])

    result = []

    for file in tqdm(files):
        data = read_json(file)

        data = data[:-3]

        question_text = data[1]['content'][0]['text'].replace("New task:\n", "")

        if question_text in filtered_questions:
            # filter out
            continue

        temp = []
        for entry in data:
            # Replace role with simplified role
            entry['role'] = role_replacement.get(entry['role'], entry['role'])
            entry['content'] = entry['content'][0]['text']

            # Truncate large accessibility tree in content if necessary
            if "The accessibility tree is:\n\n" in entry['content']:
                parts = entry['content'].split("The accessibility tree is:\n\n")
                webtext = " ".join(parts[0].split()[:2000])

                after_tree_parts = parts[1].split("Last output from code snippet:")
                accessibility_tree = after_tree_parts[0][:2000]
                code_result = "Last output from code snippet:" + after_tree_parts[-1]

                entry['content'] = f"{webtext}\n\nThe accessibility tree is:\n\n{accessibility_tree}{code_result}"

            temp.append(entry)

        # Remove last user message if present
        if temp and temp[-1]['role'] == 'user':
            temp = temp[:-1]

        if _planning and len(temp) > 4:
            # Merge the initial plan step
            plan_step = temp[2]
            plan_next = temp[3]

            plan_next['content'] = plan_next['content'].replace("<think></think>", "")
            plan_step['content'] += "\n\n **Here is my solution:**\n\n" + plan_next['content']

            new_temp = temp[:2] + [plan_step] + temp[4:]
            formatted = prepend_token({"messages": new_temp}) if _thinking else {"messages": new_temp}
            result.append(formatted)
        else:
            # Skip the 3rd message if not planning mode
            new_temp = temp[:2] + temp[3:]
            formatted = prepend_token({"messages": new_temp}) if _thinking else {"messages": new_temp}
            result.append(formatted)

    return result


def main(format_type, input_path, ref_file=None, output_file=None, planning=False, thinking=False):
    """
    Args:
        format_type (str): 'formatQuery' or 'formatTrajectory'
        input_path (str): Input file (formatQuery) or directory path (formatTrajectory)
        ref_file (str): Reference file path (optional, only for formatTrajectory)
        output_file (str): Output JSONL file path (optional)
        planning (bool): Whether to enable planning (only for formatTrajectory)
        thinking (bool): Whether to prepend think tokens (only for formatTrajectory)
    """
    if not output_file:
        raise Exception("Please specify the output_file.")
            
    if format_type == "formatQuery":
        data = read_json(input_path)
        formatted = formattingQuery(data)
        write_jsonl(formatted, output_file)


    elif format_type == "formatTrajectory":
        formatted = formattingTrajectory(
            path=input_path,
            ref_file=ref_file,
            _planning=planning,
            _thinking=thinking
        )
        write_json(formatted, output_file)
        
    else:
        raise ValueError(f"Unsupported format_type: {format_type}")


if __name__ == "__main__":
    fire.Fire(main)