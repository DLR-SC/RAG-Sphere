SYSTEM_PROMPT = "You are provided with multiple information.\n\
As you are an expert in understanding and comprehension, you will summarize all the provided Information into natural language using whole sentences.\n\
You will also add a label to the new description, which will be at most 5 words long.\n\
Remember to only use the information provided to you and to summarize all of it into a single description and label.\n\
Answer using a single JSON Object!"

ANSWER_FORMAT = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "description": {"type": "string"}
    },
    "required": ["label", "description"]
}

USER_PROMPT = "Here is the provided information:\n{information}"
