import os
import logging
from typing import Optional
from datetime import datetime

import boto3
import watchtower


def setup_logging(
    cloudwatch_log_group: str = '/aws/image-quality-analyzer',
    aws_region: Optional[str] = None,
    aws_access_key: Optional[str] = None,
    aws_secret_key: Optional[str] = None
) -> logging.Logger:
    log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(__name__)

    try:
        if not aws_region:
            aws_region = os.getenv('AWS_REGION')
        if not aws_access_key:
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        if not aws_secret_key:
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if all([aws_region, aws_access_key, aws_secret_key]):
            cloudwatch_client = boto3.client(
                'logs',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )

            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group=cloudwatch_log_group,
                stream_name=f'stream-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}',
                boto3_client=cloudwatch_client,
                send_interval=1,
                create_log_group=True
            )
            cloudwatch_handler.setLevel(log_level)
            cloudwatch_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(cloudwatch_handler)
            logger.info(f"CloudWatch logging enabled: {cloudwatch_log_group}")
        else:
            logger.warning("CloudWatch logging disabled: missing AWS credentials")
    except Exception as e:
        logger.warning(f"Failed to initialize CloudWatch logging: {str(e)}")

    return logger
