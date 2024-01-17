from argparse import ArgumentParser
from datetime import datetime
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import pandas as pd
from tqdm import tqdm

tqdm.pandas()
load_dotenv()

class GetDataFromMongo:
    """Gets queries/answers/chunks from mongo
    Usage :
    ```py
    mongo = GetDataFromMongo(os.getenv("MONGO_CONNECTION_STRING"))
    data = mongo(llm_app_id="myllmappid")
    ```
    You may provide an llm_app_id or organization_id
    """
    def __init__(self, connection_string:str, db_name:str="ProdSemantics"):
        """_summary_

        Args:
            connection_string (str): the mongoDB connection string
            db_name (str, optional): the db to query. Defaults to "ProdSemantics".

        """
        self.connection_string = connection_string

        if not db_name in ["DevSemantics", "PreprodSemantics", "ProdSemantics"]:
            raise ValueError(f'"db_name" sould be one of ["DevSemantics", "PreprodSemantics", "ProdSemantics"]. Got {db_name}')
        else:
            self.db_name = db_name
            self.db = MongoClient(self.connection_string)[self.db_name]
            print(f"Data will be fetched from {db_name}")


    def __call__(self, 
        *args,
        **kwargs
        ) -> pd.DataFrame:
        llm_app_data = self.query_QueryExecutionStep_collection(*args, **kwargs)
        dataset = GetDataFromMongo.from_query_result_to_dataset(llm_app_data)
        print(f"Query returned {len(dataset)} results...")
        print("Formatting chunks...")
        dataset["chunks"] = dataset["chunks"].progress_apply(self.format_chunks)

        return dataset
        

    def query_QueryExecutionStep_collection(
        self,
        llm_app_id:str=None,
        organization_id:str=None,
        more_recent_than:str=None,
        **kwargs) -> pd.DataFrame:
        """Queries MongoDB for user data from a specific llm_app_id or organization_id
        You may provide an llm-app_id or organization_id but not both

        Args:
            llmapp_id (str): the llm_app_id we waant data for
            organization_id (str): the organization_id we want data for
            more_recent_than (str, optional): a date, in Y-M-D format, as a string indicating the oldest queries to look for. 
                By default it will look for all queries. Example : "2021-01-01"

        Returns:
            pd.DataFrame: the raw result of the query
        """
        if (not llm_app_id and not organization_id)\
        or (llm_app_id and organization_id):
            raise ValueError(f'You must provide a value for llm_app_id or organization_id but not both')
        
        filter_dict = {"llm_app_id": {"$eq": ObjectId(llm_app_id)}} if llm_app_id else {"organization_id": {"$eq": ObjectId(organization_id)}}
        if more_recent_than:
            filter_dict["created_at"] = {"$gte":datetime.strptime(more_recent_than, "%Y-%m-%d")}

        collection_name = self.db["QueryExecutionStep"]
        query_results = collection_name.find(filter=filter_dict)
        query_results = pd.DataFrame(query_results)

        if len(query_results) == 0:
            raise KeyError(f'The query to "{self.db_name}" with filter "{filter_dict}" did not return any result.')
        
        return query_results
    

    @staticmethod
    def from_query_result_to_dataset(mongo_result_df:pd.DataFrame) -> pd.DataFrame:
        """Parses the results of the query to the QueryExecutionStep collection.
        Essentially remove useless info, and concatenate the results so that
        the 3 rows corresponding to 1 conversation is merged into 1 row

        Args:
            mongo_result_df (pd.DataFrame): the result of query_QueryExecutionStep_collection()

        Returns:
            pd.DataFrame: the parsed results. 
        """
        df_constructor = []
        for query_exec_id in mongo_result_df["query_execution_id"].unique():
            tmp = {}
            tmp_df = mongo_result_df[mongo_result_df["query_execution_id"] == query_exec_id] # get the 3 lines of df that corresponds to this query_excecution_id
            tmp["query_execution_id"] = query_exec_id
            tmp["created_at"] = tmp_df["created_at"].iloc[0]
            tmp["organization_id"] = tmp_df["organization_id"].iloc[0]
            tmp["llm_app_id"] = tmp_df["organization_id"].iloc[0]
            tmp["llm_app_type"] = tmp_df["llm_app_type"].iloc[0]
            tmp["query"] = tmp_df[tmp_df["type"] == "EMBEDDINGS"]["query"].iloc[0]["text"]
            tmp["chunks"] = tmp_df[tmp_df["type"] == "SEMANTIC_SEARCH"]["response"].iloc[0]["hits"]["hits"]
            tmp["answer"] = tmp_df[tmp_df["type"] == "STREAMING_QUESTION_ANSWERING"]["response"].iloc[0]
            tmp["created_at"] = tmp_df["created_at"].iloc[0]
            df_constructor.append(tmp)

        return pd.DataFrame(df_constructor)


    def get_chunk_text(self, chunk_id:str):
        """Get the text of a chunks using it's id

        Args:
            chunk_id (str): the id of the chunk
        """
        collection_name = self.db["DocumentChunk"]
        query_results = collection_name.find_one(filter={"_id": {"$eq": ObjectId(chunk_id)}})
        if not query_results:
            print(f"chunk_id '{chunk_id}' did not match any chunk in {self.db_name}.DocumentChunk")
            return ""
        return query_results["data"]
    

    def format_chunks(self, chunks:list[dict]):
        """From a list of chunks returned from mongo:
        - get the text
        - remove useless info
        - format
        Example :
        [{'_index': 'prod-sem-6585977b875bdeef2f737584-assistant-conversationnel-ladrome.fr',
        '_id': '6585695b875bdeef2f7373f3',
        '_score': 1.7945973,
        '_source': {'data_source_id': '6585693d27fd2cc06632e700',
        'document_id': '65856950875bdeef2f7372fd',
        'chunk_id': '65856950875bdeef2f737309',
        'chunk_embeddings_id': '6585695b875bdeef2f7373f3'}}]

        Args:
            chunks (list[dict]): list of chunks
        """
        chunk_ids = [c["_source"]["chunk_id"] for c in chunks]
        scores = [c["_score"] for c in chunks]
        texts = [self.get_chunk_text(i) for i in chunk_ids]

        chunks = [{"text": t, "_id": i, "score": s} for t, i, s in zip(texts, chunk_ids, scores)]

        return chunks


def parse_arguments():
    """ Parse the given command-line arguments. """

    parser = ArgumentParser(description="Getting data from MongoDB")

    parser.add_argument("--llm_app_id", type=str, default=None, help="The LLM App id")
    parser.add_argument("--organization_id", type=str, default=None, help="The organization id")
    parser.add_argument("--db_name", choices=["DevSemantics", "PreprodSemantics", "ProdSemantics"], default="ProdSemantics", help="The name of the DB")
    parser.add_argument("--more_recent_than", default=None, help="The max date to get data from. Format Y-m-d. Example : 2024-01-26")
    parser.add_argument("--output", default="output.csv", help="Output filename")

    return parser.parse_args()


def main():
    args = parse_arguments()

    connection_string = os.getenv("MONGO_CONNECTION_STRING")
    if not connection_string:
        raise ValueError('Environnment variable not found : MONGO_CONNECTION_STRING')
    mongo = GetDataFromMongo(connection_string, args.db_name)
    data = mongo(args.llm_app_id, args.organization_id, args.more_recent_than)
    data.to_csv(args.output)


if __name__ == "__main__":
    main()