import os
import logging
import asyncio
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from image_loader import load_images_from_folder
from model import ImageQuality

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()

# Access them like regular environment variables
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
model_id = os.getenv("MODEL_ID")

llm = ChatBedrockConverse(
    model_id=model_id,
    provider="anthropic",
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    temperature=0
)

parser = JsonOutputParser(pydantic_object=ImageQuality)

async def process_images():
    # Get all images from the images folder
    images = load_images_from_folder("images")

    for image in images:
        system_prompt = SystemMessage("Use ImageQualityEnum to determine each picture's quality")
        
        format_instruction = SystemMessage(f"format_instructions: {parser.get_format_instructions()}")

        human_message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.media_type};base64,{image.base64}"}
                }
            ]
        )

        prompt = ChatPromptTemplate.from_messages([
            system_prompt,
            format_instruction,
            human_message,
        ])

        chain = prompt | llm | parser

        ai_msg = await chain.ainvoke({})

        print(ai_msg)

if __name__ == "__main__":
    asyncio.run(process_images())

