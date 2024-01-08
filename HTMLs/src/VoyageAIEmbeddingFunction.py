import os
from dotenv import load_dotenv
import tiktoken
import voyageai as vai
from chromadb import EmbeddingFunction, Documents, Embeddings

# load the API key from .env
load_dotenv()

class VoyageAIEmbeddingFunction(EmbeddingFunction):
    def __init__(self,
            model_name:str="voyage-lite-01",
            max_token_length:int=4096,
            ):
        self.model_name = model_name
        self.max_token_length = max_token_length
        # Use tiktoken to compute token length
        # As we may not know the exact tokenizer used for the model, we generically use the one of adav2
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        vai.api_key = os.environ.get("VOYAGE_API_KEY", None)


    def truncate_sentences(self, sentences:Documents) -> Documents:
        """Truncates the sentences considering the max context window of the model

        Args:
            sentences (Documents): a list a sentences (documents)

        Returns:
            Documents: the truncated documents
        """
        for i, s in enumerate(sentences):
            tokenized_strings = self.tokenizer.encode(s)
            # if string too large, truncate, decode, and replace
            if len(tokenized_strings) > self.max_token_length:
                s = s[:self.max_token_length]
                sentences[i] = self.tokenizer.decode(s)
        return sentences


    def __call__(self, input: Documents) -> Embeddings:
        input = self.truncate_sentences(input)
        embeddings = vai.get_embeddings(input, model=self.model_name, input_type=None)
        return embeddings

