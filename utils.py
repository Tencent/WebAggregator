import json


def read_json(file):
    with open(file, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(file):
    with open(file, encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]


def write_json(data, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def write_jsonl(data, file):
    with open(file, "w", encoding='utf-8') as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

