import json
import os
from typing import Any, Callable

from dotenv import load_dotenv
from openai import OpenAI
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from tqdm import tqdm

load_dotenv()

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


class RAGDatasetGenerator:
    def __init__(self, 
        provider:str="openai",
        model:str="gpt-3.5-turbo",
        temperature:float=1.,
        max_tokens:int=1000,
        **kwargs
        ):
        """Initializes a dataset generator. It allows to quickly call 
        llms with custom templates.

        Args:
            provider (str, optional): the llm provider. Defaults to "openai".
            model (str, optional): the model name. Defaults to "gpt-3.5-turbo".
            temperature (float, optional): the temperature. See the docs for more info. Defaults to 1.
            max_tokens (int, optional): the max token for the generated answers. Defaults to 1000.
        """
        self.prompt_folder = "./prompts"
        self._provider = None

        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def provider(self):
        return self._provider
    
    @provider.setter
    def provider(self, value):
        value = value.lower()
        if value not in ["mistral", "openai"]:
            raise ValueError(f"'provider' argument should be either 'openai' or 'mistral'. Got {value}")
        elif value == "mistral" and not os.getenv("MISTRAL_API_KEY"):
            raise ValueError("Missing environment variable: API key to access to Mistral AI (MISTRAL_API_KEY)")
        elif value == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Missing environment variable: API key to access to OpenAI (OPENAI_API_KEY)")
        else:
            self._provider = value
            self.client = self.get_providers_client()

    @property
    def prompts(self):
        return {
            "generate_questions": self.read_prompt("./generate_questions.txt"),
            "generate_answer": self.read_prompt("./generate_answer.txt"),
            "generate_short_answer": self.read_prompt("./generate_short_answer.txt")
        }


    def get_providers_client(self):
        match self.provider:
            case "openai":
                api_key = os.environ["OPENAI_API_KEY"]
                return OpenAI(api_key=api_key)
            case "mistral":
                api_key = os.environ["MISTRAL_API_KEY"]
                return MistralClient(api_key=api_key)
            case other:
                raise Exception(f"Provider not supported : {other}")


    def read_prompt(self, prompt_filename:str) -> str:
        """Reads a txt file containing the prompt

        Args:
            prompt_filename (str): name of file containing the prompt

        Returns:
            (str) -> the prompt
        """
        with open(os.path.join(self.prompt_folder, prompt_filename)) as f:
            prompt = f.read()

        return prompt
    

    def call_model(self, prompt:str, parsing_function:Callable=None, max_retries:int=3, **kwargs):
        """Calls the models and parses the output using parsing_funtion.
        This function must return the parsed output, or None if the output
        couldn't be parsed
        Args:
            model (str): the name of the model
            parsing_function (Callable): the function ot use for parsing the output.
            max_retries (int): the max number of retries

        Raises:
            Exception: if the specified provided is not supported

        Returns:
            _type_: the model
        """
        retry = 0
        response = None
        while retry < max_retries and not response:
            match self.provider:
                case "openai":
                    response = self.call_openai(prompt)
                    response = response.choices[0].message.content
                case "mistral":
                    response =  self.call_mistral(prompt)
                    response = response.choices[0].message.content
                case other:
                    raise Exception(f"Provider not supported : '{other}'")
            if parsing_function:
                response = parsing_function(response, **kwargs)
            retry += 1

        return response
            

    def call_openai(self, prompt):

        messages = [
                {"role": "user", "content": prompt}
            ]
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=messages
        )
        return response
        

    def call_mistral(self, prompt:str):
        """Calls the mistral model for chat completion

        Args:
            prompt (str): the prompt to call the model for

        Returns:
            any: the response
        """

        messages = [
            ChatMessage(role="user", content=prompt)
        ]
        response = self.client.chat(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response


    def generate_questions_from_chunk(self, context:str, question_number:int=3, language:str="french", **kwargs) -> list[str]:
        """From a given context (= piece of text), generates questions.

        Args:
            context (str): the piece of text from which to generate questions from
            question_number (int, optional): the amount of questions. Defaults to 3.
            language (str, optional): the language. Defaults to "french".

        Returns:
            (list[str]) : the list of questions
        """
        variables = dict(context=context, question_number=question_number, language=language)
        prompt = self.prompts["generate_questions"].format(**variables)
        kwargs["elems_in_list"] = question_number
        response = self.call_model(prompt, self.parse_list_of_strings, **kwargs)

        return response
    

    def parse_list_of_strings(self, content, elems_in_list:int=3, **kwargs):
        """Parses the response of the model and checks its a list of string

        Args:
            response (str): the content (=text) of the llm's response
            elems_in_list (int, optional): amount of elements to keep. Defaults to 3.

        Returns:
            _type_: _description_
        """
        try:
            content = json.loads(content)
            if isinstance(content, list):
                return content[:elems_in_list]
        except Exception:
            print(f"Generated content is not list of strings : {content} . \nRetrying...")
            return None
        

    def generate_answer(self, question:str, context:str, short=False, **kwargs) -> str:
        """From a given context (= piece of text) and question, generates answer.
        If short=True, the n the answer will likely be just the element representing the answer
        without extra explanation

        Args:
            question (str): the question to answer to
            context (str): the piece of text from which to generate questions from
            short (bool): whether or not we want short or long answer

        Returns:
            (str) : the answer to the question
        """
        variables = dict(context=context, question=question)
        if short:
            prompt = self.prompts["generate_short_answer"].format(**variables)
            response = self.call_model(prompt, self.parse_list_of_strings, **kwargs)
        else:
            prompt = self.prompts["generate_answer"].format(**variables)
            response = self.call_model(prompt, None, **kwargs)

        return response
    

    def generate_RAG_dataset(self, chunks_dir:str, filenames:list[str]=[], keys_to_text:list[Any]=["text"]) -> None:
        """Generates a RAG dataset from texts. The dataset is saved in the parent
        directory of chunks_dir.

        If no filenames is provided, then all the content of chunk_dir is considered as chunk files.
        The chunk files must be json files. List of keys to reach the text content can be provided. By default, it will get a "text" key.

        Args:
            chunks_dir (str): path where the chunks are saved. 
            filenames (list[str], optional): _description_. Defaults to [].
            keys_to_text (list[Any], optional): list of keys to reach the text of the chunk
        """
        if isinstance(filenames, str):
            filenames = [filenames]
        if not filenames:
            filenames = os.listdir(chunks_dir)
        
        records = []
        for filename in tqdm(filenames):
            text = RAGDatasetGenerator._get_text_from_json(
                os.path.join(chunks_dir, filename),
                keys_to_text)
            
            question = self.generate_questions_from_chunk(text, 1)[0]
            answer = self.generate_answer(question, text)
            short_answer = self.generate_answer(question, text, short=True)
            records.append({
                "query": question,
                "long_answer": answer,
                "short_answer": short_answer,
                "relevant_ids": filename
            })

        save_path = os.path.join(os.path.dirname(chunks_dir), f"generated_data_{self.model.replace('.', '-')}.json")
        with open(save_path, "w") as f:
            json.dump(records, f)
            print(f"Dataset saved at : {save_path}")


    @staticmethod
    def _get_text_from_json(filepath, keys_to_text):
        with open(filepath, "r") as f:
            chunk_dict = json.load(f)
        for key in keys_to_text:
            chunk_dict = chunk_dict[key]

        return chunk_dict
        
