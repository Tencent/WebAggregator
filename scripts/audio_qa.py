from typing import Optional
from pydub import AudioSegment

from smolagents import Tool,AzureOpenAIServerModel
    
from openai import AzureOpenAI
from openai import OpenAI

import json

from ..config import text_client

class Whisper:
    def __init__(self):
        openai_api_key = "EMPTY"
        openai_api_base = "your_url"
        
        self.client = OpenAI(
        # defaults to os.environ.get("OPENAI_API_KEY")
        api_key=openai_api_key,
        base_url=openai_api_base,
        )
        models = self.client.models.list()
        self.model = models.data[0].id
    def sync_openai(self, file):
        with open(file, "rb") as f:
            transcription = self.client.audio.transcriptions.create(
                file=f,
                model=self.model,
                language="en",
                response_format="json",
                temperature=0.0)
        return transcription.text

whisper = Whisper()


def audio_split_and_transcript(input_file):
    # Construct the output filename template for audio chunks
    output_file = "downloads/cache/" + input_file.split("/")[-1].split(".")[0] + "-{}.ogg"
    
    # Load the input MP3 audio file with pydub
    audio = AudioSegment.from_mp3(input_file)
    print(">>>>>audio loaded<<<<<")
    
    # Get the audio duration in milliseconds
    duration_milliseconds = len(audio)
    # Convert duration to seconds, rounding up
    duration_seconds = int(duration_milliseconds / 1000.0 + 1)
    
    chunk_size = 30  # Length of each chunk in seconds
    overlap = 10     # Overlap between adjacent chunks in seconds

    # Calculate the number of chunks needed (with overlap)
    num_chunks = (duration_seconds - overlap) // (chunk_size - overlap) + 1

    results = {}
    for i in range(num_chunks):
        start = i * (chunk_size - overlap)  # Start time (in seconds) for the chunk
        end = start + chunk_size            # End time (in seconds) for the chunk
        # Extract the audio chunk (convert times to milliseconds)
        chunk = audio[start * 1000 : end * 1000]
        # Export the audio chunk to .ogg file
        chunk.export(output_file.format(f"{start}:{end}"), format="ogg")
        # Transcribe the chunk using whisper.sync_openai, and store the result
        results[f"{start}:{end}"] = whisper.sync_openai(output_file.format(f"{start}:{end}"))
        
    return results


def merge(transcription:dict) -> str:
    prompt = """
Here is the result of converting an audio slice into text. 
Since the model for speech-to-text (STT) can accept audio of up to 30 seconds in length at most, 
the audio was sliced, and the results were placed in a JSON file in the order of the slice times.
The file format looks like: `{"0:30", "transcript","20:50", "transcript"}`.
To prevent loss of information, the audio slices overlap. 
Therefore, please integrate the entire JSON and return the transcript of the complete audio.
The format should be: `{"result":merged transcript}`.
Let's get started:
    """
    
    response = text_client["server"].chat.completions.create(
        model=text_client["model_id"], # model = "deployment_name".
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + json.dumps(transcription)},
                    ],
                }
            ]
    )
    return response.choices[0].message.content

def audio_qa(question, transcription):
    prompt = """
Below is the text transcribed from an audio. 
Please answer the questions based on the text.

Transcript: {}

Question: {}"""


    response = text_client["server"].chat.completions.create(
        model=text_client["model_id"], # model = "deployment_name".
        messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + json.dumps(transcription)},
                    ],
                }
            ]
    )
    return response.choices[0].message.content

class AudioQATool(Tool):
    name = "audio_qa"
    description = """A tool that can transcript the attached audio file to text, including [".mp3",".wav", ".ogg"]."""

    inputs = {
        "audio_path": {
            "description": "The path to the audio on which to answer the question",
            "type": "string",
        },
        "question": {"description": "the question to answer", "type": "string", "nullable": True},
    }
    output_type = "string"
    
    def forward(self, audio_path: str, question: Optional[str] = None) -> str:
        
        if "data/" in audio_path:
            audio_path = "data/"+audio_path.split("data/")[-1]
        print(audio_path)
        transcription = audio_split_and_transcript(audio_path)

        complete_transcription = json.loads(merge(transcription))
        if question is not None:
            answer = audio_qa(question, complete_transcription)
            ans_prompt = "Here is the complete transcription of the audio file"
            result = {f"{ans_prompt} {audio_path} : \n":complete_transcription['result'],
                  "Answer to the Question: \n": answer}
        else:
            result = {f"{ans_prompt} {audio_path} : \n":complete_transcription['result']}
        
        string = ""
        for k,v in result.items():
            string += f"{k} {v}\n\n"
        return string
    