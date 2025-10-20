import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int: 
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by GPT-4)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))