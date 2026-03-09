import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

from discrepancy_explainer import DiscrepancyExplainer
from image_loader import load_image_as_base64

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

llm = ChatBedrockConverse(
    model_id=os.getenv("MODEL_ID"),
    provider="anthropic",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0,
)


async def main():
    benchmark = load_image_as_base64(Path("images/image.png"))
    live_frame = load_image_as_base64(Path("images/image copy.png"))

    explainer = DiscrepancyExplainer(logging.getLogger(__name__), llm)
    result = await explainer.explain(benchmark, live_frame, "cam-test")
    print(result.model_dump_json(indent=2))


asyncio.run(main())
