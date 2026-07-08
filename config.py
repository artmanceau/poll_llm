MODEL = "llama3.2"

N_RESPONDENTS = 50
WORKERS = 32

QUOTA_FILE = "quotas/quotas.csv"
PROMPT_FILE = "prompts/persona.jinja2"

PROMPT_S3_PATH = (
    "s3://arthurmanceau/poll_llm/01_prompts/"
)

RESULT_FILE = "results/results.parquet"