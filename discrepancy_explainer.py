import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from image_loader import ImageObject
from model import VisualContext


class DiscrepancyExplainer:
    def __init__(self, logger: logging.Logger, llm):
        self._logger = logger
        self._llm = llm
        self._parser = JsonOutputParser(pydantic_object=VisualContext)

    async def explain(
        self,
        benchmark_image: ImageObject,
        live_frame: ImageObject,
        camera_id: str,
    ) -> VisualContext:
        system_message = SystemMessage(
            "You are analyzing a surveillance camera feed. You will be given two images:\n"
            "1) A benchmark image representing the expected normal view for this camera.\n"
            "2) A live frame captured recently from the same camera.\n\n"
            "Describe what you observe in the live frame compared to the benchmark.\n"
            "Do not classify quality as good or bad. Focus on:\n"
            "- What visually differs between the two images\n"
            "- Where in the frame the difference appears\n"
            "- What might have caused it (physical, environmental, or technical)"
        )

        format_instructions = SystemMessage(
            f"format_instructions: {self._parser.get_format_instructions()}"
        )

        human_message = HumanMessage(
            content=[
                {"type": "text", "text": "Benchmark image:"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{benchmark_image.media_type};base64,{benchmark_image.base64}"},
                },
                {"type": "text", "text": "Live frame:"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{live_frame.media_type};base64,{live_frame.base64}"},
                },
            ]
        )

        chain = self._llm | self._parser

        self._logger.info("Explaining discrepancy for camera %s", camera_id)
        result = await chain.ainvoke([system_message, format_instructions, human_message])
        return VisualContext(**result)
