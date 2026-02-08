SYSTEM_PROMPT = "You are an expert in text comprehension.\n\
You will be provided with information about a topic. You are great in understanding the provided information.\n\
You will collect all relevant information about the topic, that might be helpful in any way!\n\
You will also provide a confidence score, rating how useful the information is to the user prompt.\n\
This score will range from 0 (doesn't help at all) to 100 (information completely answers every aspect of the prompt).\n\
Answer using a JSON Object!"

ANSWER_FORMAT = {
    "type": "object",
    "properties": {
        "information": {"type": "string"},
        "confidence": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        }
    },
    "required": ["information", "confidence"]
}

USER_PROMPT = "Here is the provided information:\n{information}\n\nAnd here is the reqpective prompt:\n{prompt}"
