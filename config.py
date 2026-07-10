MODEL = "qwen3:8b"
N_RESPONDENTS = 500
WORKERS = 32
YEAR = 2027

PROMPT_FILE = "poll_llm/prompts/poll_question.jinja2"

RESULT_FILE = "s3://arthurmanceau/poll_llm/results/detailed"
RESULT_FILE_SUMMARY = "s3://arthurmanceau/poll_llm/results/summary"